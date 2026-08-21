#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import math
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.tree import DecisionTreeClassifier, export_text

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_FRESH_4H_FIRST_PULLBACK_B22D_Result.md'
OUT_JSON = ROOT / 'BTC_FRESH_4H_FIRST_PULLBACK_B22D_Result.json'
OUT_SUMMARY = ROOT / 'BTC_FRESH_4H_FIRST_PULLBACK_B22D_Strategy_Summary.csv'
OUT_EVENTS = ROOT / 'BTC_FRESH_4H_FIRST_PULLBACK_B22D_Events.csv'
OUT_FORENSIC = ROOT / 'BTC_FRESH_4H_FIRST_PULLBACK_B22D_Fakeout_Forensics.csv'
OUT_CHAMP = ROOT / 'BTC_FRESH_4H_FIRST_PULLBACK_B22D_Champion_Trades.csv'

PARTS = b22b.PARTS
ENTRY_TFS = {'5m': ('5min', pd.Timedelta(minutes=5)), '15m': ('15min', pd.Timedelta(minutes=15))}
REGIMES = ['R4_FRESH', 'R1H4_FRESH']
EXITS = ['X_1H_WEAK', 'X_4H_WEAK']
SEARCH_HORIZON = pd.Timedelta(hours=48)
LABEL_HORIZON = pd.Timedelta(hours=24)

FEATURES = [
    'activation_age_h', 'activation_bars_4h',
    'h4_spread', 'h4_spread_chg3', 'h4_ema20_slope3', 'h4_ema50_slope3', 'h4_ext20', 'h4_atr_pct',
    'h1_strong', 'h1_spread', 'h1_ema20_slope3', 'h1_ema50_slope3', 'h1_ext20', 'h1_ret3', 'h1_atr_pct',
    'pb_low_band_pos', 'pb_close_ext20', 'reclaim_body_range', 'reclaim_clv', 'reclaim_ext20',
    'reclaim_range_pct', 'ltf_spread', 'ltf_ema20_slope3',
    'flow_15m', 'flow_30m', 'flow_60m', 'volume_expansion_60m', 'ret_60m',
]


def _fetch_full(url: str):
    r = requests.get(url, timeout=90, headers={'User-Agent': 'bababot-b22d/1.0'})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            z = pd.read_csv(
                fh, header=None, usecols=[0,1,2,3,4,7,10],
                names=['ts','open','high','low','close','quote_volume','taker_buy_quote']
            )
    return z


def load5_full():
    frames = []
    urls = b21._urls()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_fetch_full, u): u for u in urls}
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError('No Binance 5m data downloaded')
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors='coerce')
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x['ts'] = pd.to_datetime(t, unit='ms', utc=True, errors='coerce')
    for c in ['open','high','low','close','quote_volume','taker_buy_quote']:
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna().drop_duplicates('ts').sort_values('ts')
    x = x[(x.ts >= b21.FETCH_START) & (x.ts < b21.END)].set_index('ts')
    idx = x.index
    expected = int((idx[-1] - idx[0]) / pd.Timedelta(minutes=5)) + 1
    coverage = len(x) / expected
    if len(x) < 650_000 or coverage < .995:
        raise RuntimeError(f'Insufficient 5m data rows={len(x)} coverage={coverage:.6f}')
    x['signed_quote'] = 2.0 * x.taker_buy_quote - x.quote_volume
    x['qv60'] = x.quote_volume.rolling(12, min_periods=12).sum()
    x['qv60_prior24_median'] = x.qv60.shift(1).rolling(288, min_periods=144).median()
    return x, coverage


def resample_full(x: pd.DataFrame, rule: str):
    if rule == '5min':
        return x[['open','high','low','close','quote_volume','signed_quote']].copy()
    return x[['open','high','low','close','quote_volume','signed_quote']].resample(
        rule, origin='start_day', label='left', closed='left'
    ).agg({'open':'first','high':'max','low':'min','close':'last','quote_volume':'sum','signed_quote':'sum'}).dropna()


def enrich(frame: pd.DataFrame):
    z = b22b.enrich(frame[['open','high','low','close']])
    z['quote_volume'] = frame.quote_volume
    z['signed_quote'] = frame.signed_quote
    prev = z.close.shift(1)
    tr = pd.concat([(z.high-z.low), (z.high-prev).abs(), (z.low-prev).abs()], axis=1).max(axis=1)
    z['atr14'] = tr.rolling(14, min_periods=14).mean()
    z['atr_pct'] = z.atr14 / z.close
    z['spread_chg3'] = z.spread - z.spread.shift(3)
    z['ema20_slope3'] = (z.ema20 - z.ema20.shift(3)) / z.close
    z['ema50_slope3'] = (z.ema50 - z.ema50.shift(3)) / z.close
    z['ext20'] = (z.close - z.ema20) / z.close
    z['ret3'] = z.close / z.close.shift(3) - 1.0
    return z


def map_avail(series: pd.Series, duration: pd.Timedelta, target_close: pd.DatetimeIndex, boolean=False):
    s = series.copy()
    s.index = s.index + duration
    out = s.reindex(target_close, method='ffill')
    if boolean:
        return out.fillna(False).astype(bool).to_numpy()
    return pd.to_numeric(out, errors='coerce').to_numpy(float)


def partition_of(t: pd.Timestamp):
    for p, (a,b) in PARTS.items():
        if a <= t < b:
            return p
    return None


def activation_episodes(h4: pd.DataFrame):
    s = h4.strong.fillna(False).astype(bool)
    act = np.where((s & ~s.shift(1, fill_value=False)).to_numpy())[0]
    out = []
    for i in act:
        act_avail = h4.index[i] + pd.Timedelta(hours=4)
        j = i + 1
        while j < len(h4) and bool(s.iloc[j]):
            j += 1
        off_avail = (h4.index[j] + pd.Timedelta(hours=4)) if j < len(h4) else b21.END
        out.append((i, act_avail, off_avail))
    return out


def flow_features(x5: pd.DataFrame, signal_close: pd.Timestamp):
    end = int(x5.index.searchsorted(signal_close, side='left'))
    if end < 300:
        return {k: np.nan for k in ['flow_15m','flow_30m','flow_60m','volume_expansion_60m','ret_60m']}
    vals = {}
    for n, name in [(3,'flow_15m'),(6,'flow_30m'),(12,'flow_60m')]:
        q = x5.iloc[end-n:end]
        denom = float(q.quote_volume.sum())
        vals[name] = float(q.signed_quote.sum()/denom) if denom > 0 else np.nan
    last = x5.iloc[end-1]
    base = float(last.qv60_prior24_median) if pd.notna(last.qv60_prior24_median) else np.nan
    vals['volume_expansion_60m'] = float(last.qv60/base) if pd.notna(base) and base > 0 else np.nan
    q = x5.iloc[end-12:end]
    vals['ret_60m'] = float(q.iloc[-1].close/q.iloc[0].open - 1.0)
    return vals


def fakeout_label(x5: pd.DataFrame, entry_ts: pd.Timestamp, entry_px: float, atr1h_abs: float,
                  weak_now: bool, h1_weak_times: pd.DatetimeIndex):
    if not pd.notna(atr1h_abs) or atr1h_abs <= 0:
        return 'AMBIGUOUS', None, None
    end_t = entry_ts + LABEL_HORIZON
    target = entry_px + atr1h_abs
    lo = int(x5.index.searchsorted(entry_ts, side='left'))
    hi = int(x5.index.searchsorted(end_t, side='left'))
    hit_t = None
    for i in range(lo, min(hi, len(x5))):
        if float(x5.iloc[i].high) >= target:
            hit_t = x5.index[i] + pd.Timedelta(minutes=5)
            break
    if weak_now:
        weak_t = entry_ts
    else:
        j = int(h1_weak_times.searchsorted(entry_ts, side='left'))
        weak_t = h1_weak_times[j] if j < len(h1_weak_times) and h1_weak_times[j] <= end_t else None
    if weak_t is not None and (hit_t is None or weak_t <= hit_t):
        return 'FAKEOUT', hit_t, weak_t
    if hit_t is not None:
        return 'FOLLOWTHROUGH', hit_t, weak_t
    return 'AMBIGUOUS', hit_t, weak_t


def make_event_features(z, sig_i, act_avail, close_clock, maps, x5):
    r = z.iloc[sig_i]
    prev = z.iloc[sig_i-1]
    den = float(prev.ema20 - prev.ema50)
    band_pos = float((prev.low-prev.ema50)/den) if pd.notna(den) and abs(den) > 1e-12 else np.nan
    rng = float(r.high-r.low)
    feats = {
        'activation_age_h': float((close_clock[sig_i]-act_avail)/pd.Timedelta(hours=1)),
        'activation_bars_4h': float(math.floor((close_clock[sig_i]-act_avail)/pd.Timedelta(hours=4))),
        'h4_spread': maps['h4_spread'][sig_i],
        'h4_spread_chg3': maps['h4_spread_chg3'][sig_i],
        'h4_ema20_slope3': maps['h4_ema20_slope3'][sig_i],
        'h4_ema50_slope3': maps['h4_ema50_slope3'][sig_i],
        'h4_ext20': maps['h4_ext20'][sig_i],
        'h4_atr_pct': maps['h4_atr_pct'][sig_i],
        'h1_strong': float(bool(maps['h1_strong'][sig_i])),
        'h1_spread': maps['h1_spread'][sig_i],
        'h1_ema20_slope3': maps['h1_ema20_slope3'][sig_i],
        'h1_ema50_slope3': maps['h1_ema50_slope3'][sig_i],
        'h1_ext20': maps['h1_ext20'][sig_i],
        'h1_ret3': maps['h1_ret3'][sig_i],
        'h1_atr_pct': maps['h1_atr_pct'][sig_i],
        'pb_low_band_pos': band_pos,
        'pb_close_ext20': float((prev.close-prev.ema20)/prev.close),
        'reclaim_body_range': float((r.close-r.open)/rng) if rng > 0 else np.nan,
        'reclaim_clv': float((r.close-r.low)/rng) if rng > 0 else np.nan,
        'reclaim_ext20': float((r.close-r.ema20)/r.close),
        'reclaim_range_pct': float(rng/r.close),
        'ltf_spread': float(r.spread),
        'ltf_ema20_slope3': float((r.ema20-z.iloc[sig_i-3].ema20)/r.close) if sig_i >= 3 else np.nan,
    }
    feats.update(flow_features(x5, close_clock[sig_i]))
    return feats


def build_events(x5: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame):
    episodes = activation_episodes(h4)
    h1_weak = (h1.close < h1.ema20) & (h1.ema20 < h1.ema20.shift(1))
    h4_weak = (h4.close < h4.ema20) & (h4.ema20 < h4.ema20.shift(1))
    h1_weak_times = pd.DatetimeIndex(h1.index[h1_weak.fillna(False)] + pd.Timedelta(hours=1))
    all_events = []
    contexts = {}

    for entry_tf, (rule, dur) in ENTRY_TFS.items():
        z = enrich(resample_full(x5, rule))
        close_clock = z.index + dur
        maps = {
            'r4': map_avail(h4.strong, pd.Timedelta(hours=4), close_clock, True),
            'h1_strong': map_avail(h1.strong, pd.Timedelta(hours=1), close_clock, True),
            'h1_weak': map_avail(h1_weak, pd.Timedelta(hours=1), close_clock, True),
            'h4_weak': map_avail(h4_weak, pd.Timedelta(hours=4), close_clock, True),
            'h4_spread': map_avail(h4.spread, pd.Timedelta(hours=4), close_clock),
            'h4_spread_chg3': map_avail(h4.spread_chg3, pd.Timedelta(hours=4), close_clock),
            'h4_ema20_slope3': map_avail(h4.ema20_slope3, pd.Timedelta(hours=4), close_clock),
            'h4_ema50_slope3': map_avail(h4.ema50_slope3, pd.Timedelta(hours=4), close_clock),
            'h4_ext20': map_avail(h4.ext20, pd.Timedelta(hours=4), close_clock),
            'h4_atr_pct': map_avail(h4.atr_pct, pd.Timedelta(hours=4), close_clock),
            'h1_spread': map_avail(h1.spread, pd.Timedelta(hours=1), close_clock),
            'h1_ema20_slope3': map_avail(h1.ema20_slope3, pd.Timedelta(hours=1), close_clock),
            'h1_ema50_slope3': map_avail(h1.ema50_slope3, pd.Timedelta(hours=1), close_clock),
            'h1_ext20': map_avail(h1.ext20, pd.Timedelta(hours=1), close_clock),
            'h1_ret3': map_avail(h1.ret3, pd.Timedelta(hours=1), close_clock),
            'h1_atr_pct': map_avail(h1.atr_pct, pd.Timedelta(hours=1), close_clock),
            'h1_atr_abs': map_avail(h1.atr14, pd.Timedelta(hours=1), close_clock),
        }
        base_entry = z.entry_PULLBACK_RECLAIM.fillna(False).to_numpy(bool)
        for regime in REGIMES:
            rmask = maps['r4'].copy()
            if regime == 'R1H4_FRESH':
                rmask &= maps['h1_strong']
            for act_i, act_avail, off_avail in episodes:
                part = partition_of(act_avail)
                if part is None:
                    continue
                pstart, pend = PARTS[part]
                stop = min(act_avail + SEARCH_HORIZON, off_avail, pend)
                lo = int(close_clock.searchsorted(act_avail, side='left'))
                hi = int(close_clock.searchsorted(stop, side='left'))
                sig_i = None
                for i in range(max(lo,1), min(hi, len(z)-1)):
                    if base_entry[i] and rmask[i]:
                        sig_i = i
                        break
                if sig_i is None:
                    continue
                e_i = sig_i + 1
                entry_ts = z.index[e_i]
                if entry_ts >= pend:
                    continue
                entry_px = float(z.iloc[e_i].open)
                feats = make_event_features(z, sig_i, act_avail, close_clock, maps, x5)
                label, target_hit_t, weak_t = fakeout_label(
                    x5, entry_ts, entry_px, float(maps['h1_atr_abs'][sig_i]),
                    bool(maps['h1_weak'][sig_i]), h1_weak_times
                )
                ev = {
                    'partition': part, 'entry_tf': entry_tf, 'regime': regime,
                    'activation_ts': act_avail, 'signal_ts': z.index[sig_i],
                    'signal_close_ts': close_clock[sig_i], 'entry_ts': entry_ts,
                    'entry_px': entry_px, 'label': label,
                    'target_hit_ts': target_hit_t, 'h1_weak_ts': weak_t,
                    **feats,
                }
                all_events.append(ev)
        contexts[entry_tf] = {'z': z, 'close_clock': close_clock, 'maps': maps}
    return pd.DataFrame(all_events), contexts


def simulate_event(z: pd.DataFrame, maps: dict, ev: pd.Series, exit_type: str):
    idx = z.index
    e_i = int(idx.searchsorted(pd.Timestamp(ev.entry_ts), side='left'))
    _, pend = PARTS[ev.partition]
    hi = int(idx.searchsorted(pend, side='left'))
    if e_i >= hi-1:
        return None
    xsig = maps['h1_weak'] if exit_type == 'X_1H_WEAK' else maps['h4_weak']
    x_sig = None
    for j in range(e_i, hi-1):
        if xsig[j]:
            x_sig = j
            break
    if x_sig is None:
        x_i = hi-1
        reason = 'PARTITION_FORCE_CLOSE'
    else:
        x_i = min(x_sig+1, hi-1)
        reason = exit_type if x_i < hi-1 else 'PARTITION_FORCE_CLOSE'
    if x_i <= e_i:
        return None
    entry_px = float(z.iloc[e_i].open)
    exit_px = float(z.iloc[x_i].open)
    highs = z.high.to_numpy(float); lows = z.low.to_numpy(float)
    return {
        'partition': ev.partition, 'entry_tf': ev.entry_tf, 'regime': ev.regime, 'exit_type': exit_type,
        'activation_ts': ev.activation_ts, 'entry_ts': idx[e_i], 'exit_ts': idx[x_i],
        'entry_px': entry_px, 'exit_px': exit_px, 'return': exit_px/entry_px-1.0,
        'mfe': float(np.nanmax(highs[e_i:x_i]))/entry_px-1.0,
        'mae': float(np.nanmin(lows[e_i:x_i]))/entry_px-1.0,
        'hold_hours': float((idx[x_i]-idx[e_i])/pd.Timedelta(hours=1)),
        'exit_reason': reason,
    }


def eligible(r):
    return (r.n >= 30 and pd.notna(r.win_rate) and r.win_rate >= .55
            and pd.notna(r.profit_factor) and r.profit_factor >= 1.20
            and pd.notna(r.median_return) and r.median_return > 0
            and pd.notna(r.median_mae) and r.median_mae > -.02)


def finite(v):
    try:
        f=float(v); return f if math.isfinite(f) else None
    except Exception:
        return None


def strategy_analysis(events, contexts):
    rows=[]; trade_map={}
    for entry_tf in ENTRY_TFS:
        z=contexts[entry_tf]['z']; maps=contexts[entry_tf]['maps']
        for regime in REGIMES:
            evs=events[(events.entry_tf==entry_tf)&(events.regime==regime)]
            for ex in EXITS:
                for part in PARTS:
                    trs=[]
                    for _,ev in evs[evs.partition==part].iterrows():
                        tr=simulate_event(z,maps,ev,ex)
                        if tr is not None: trs.append(tr)
                    trade_map[(part,entry_tf,regime,ex)]=trs
                    rows.append({'partition':part,'entry_tf':entry_tf,'regime':regime,'exit_type':ex,**b22b.metrics(trs)})
    s=pd.DataFrame(rows)
    dev=s[s.partition=='development'].copy(); dev['eligible']=dev.apply(eligible,axis=1)
    q=dev[dev.eligible].sort_values(['profit_factor','win_rate','n'],ascending=[False,False,False])
    champ=None; gates={'B22D_REPLICATED_CLUE':False,'HIGH_PRECISION_CLUE':False}; champ_trades=[]
    if not q.empty:
        best=q.iloc[0]; near=q[q.profit_factor>=best.profit_factor-.02]
        best=near.sort_values(['win_rate','n','profit_factor'],ascending=[False,False,False]).iloc[0]
        key=(best.entry_tf,best.regime,best.exit_type)
        pm={}
        for _,r in s[(s.entry_tf==key[0])&(s.regime==key[1])&(s.exit_type==key[2])].iterrows():
            pm[r.partition]={k:(int(r[k]) if k in ['n','max_losing_streak'] and pd.notna(r[k]) else finite(r[k]))
                             for k in ['n','win_rate','mean_return','median_return','profit_factor','median_hold_h','median_mfe','median_mae','p90_adverse','max_losing_streak']}
        oks=[]; hp=[]
        for p in ['external','reference_validation']:
            m=pm.get(p,{})
            ok=((m.get('n') or 0)>=15 and (m.get('win_rate') or 0)>=.60 and (m.get('profit_factor') or 0)>=1.20 and (m.get('median_return') or 0)>0)
            oks.append(ok); hp.append(ok and (m.get('win_rate') or 0)>=.80)
        gates={'B22D_REPLICATED_CLUE':bool(all(oks)),'HIGH_PRECISION_CLUE':bool(all(hp))}
        champ={'entry_tf':key[0],'regime':key[1],'exit_type':key[2],'partitions':pm}
        for p in PARTS: champ_trades.extend(trade_map[(p,*key)])
    return s, champ, gates, champ_trades


def smd(follow: pd.Series, fake: pd.Series):
    a=pd.to_numeric(follow,errors='coerce').dropna().to_numpy(float)
    b=pd.to_numeric(fake,errors='coerce').dropna().to_numpy(float)
    if len(a)<2 or len(b)<2:return np.nan
    va=np.var(a,ddof=1); vb=np.var(b,ddof=1)
    pooled=math.sqrt(max(((len(a)-1)*va+(len(b)-1)*vb)/(len(a)+len(b)-2),0))
    return (float(np.mean(a))-float(np.mean(b)))/pooled if pooled>0 else np.nan


def forensic_analysis(events):
    primary=events[(events.entry_tf=='5m')&(events.regime=='R4_FRESH')&events.label.isin(['FOLLOWTHROUGH','FAKEOUT'])].copy()
    rows=[]
    for feat in FEATURES:
        for part in ['development','external','reference_validation']:
            p=primary[primary.partition==part]
            a=p[p.label=='FOLLOWTHROUGH'][feat]; b=p[p.label=='FAKEOUT'][feat]
            rows.append({'feature':feat,'partition':part,'n_follow':int(pd.to_numeric(a,errors='coerce').notna().sum()),
                         'n_fake':int(pd.to_numeric(b,errors='coerce').notna().sum()),
                         'median_follow':finite(pd.to_numeric(a,errors='coerce').median()),
                         'median_fake':finite(pd.to_numeric(b,errors='coerce').median()),
                         'smd':finite(smd(a,b))})
    f=pd.DataFrame(rows)
    stable=[]
    for feat in FEATURES:
        q=f[f.feature==feat].set_index('partition')
        if not all(p in q.index for p in ['development','external','reference_validation']):continue
        d=q.loc['development']; e=q.loc['external']; v=q.loc['reference_validation']
        vals=[d.smd,e.smd,v.smd]
        counts=all(min(int(r.n_follow),int(r.n_fake))>=10 for _,r in q.iterrows())
        same=all(x is not None and pd.notna(x) for x in vals) and np.sign(vals[0])==np.sign(vals[1])==np.sign(vals[2])
        if counts and same and abs(vals[0])>=.50 and abs(vals[1])>=.15 and abs(vals[2])>=.15:
            stable.append(feat)
    f['stable_discriminator']=f.feature.isin(stable)

    tree_payload=None
    dev=primary[primary.partition=='development'].copy()
    if len(dev)>=30 and dev.label.nunique()==2:
        X=dev[FEATURES].apply(pd.to_numeric,errors='coerce')
        med=X.median(); X=X.fillna(med).fillna(0.0)
        y=(dev.label=='FOLLOWTHROUGH').astype(int)
        tree=DecisionTreeClassifier(max_depth=2,min_samples_leaf=15,class_weight='balanced',random_state=20260821)
        tree.fit(X,y)
        leaves=tree.apply(X)
        dtmp=pd.DataFrame({'leaf':leaves,'y':y.to_numpy()})
        leaf_stats=dtmp.groupby('leaf').y.agg(['count','mean']).reset_index()
        eligible_leaf=leaf_stats[leaf_stats['count']>=15].sort_values(['mean','count'],ascending=[False,False])
        if not eligible_leaf.empty:
            leaf=int(eligible_leaf.iloc[0].leaf)
            reps={}
            for part in ['development','external','reference_validation']:
                p=primary[primary.partition==part].copy()
                base=float((p.label=='FOLLOWTHROUGH').mean()) if len(p) else None
                Xp=p[FEATURES].apply(pd.to_numeric,errors='coerce').fillna(med).fillna(0.0)
                lp=tree.apply(Xp) if len(p) else np.array([])
                sel=p.iloc[np.where(lp==leaf)[0]] if len(p) else p
                rate=float((sel.label=='FOLLOWTHROUGH').mean()) if len(sel) else None
                reps[part]={'n':int(len(sel)),'follow_rate':rate,'baseline_rate':base,'lift':(rate-base if rate is not None and base is not None else None)}
            tree_payload={'selected_leaf':leaf,'rule_text':export_text(tree,feature_names=FEATURES),'partitions':reps,
                          'feature_importance':{FEATURES[i]:float(v) for i,v in enumerate(tree.feature_importances_) if v>0}}
    return f, stable, tree_payload


def pct(v):return '-' if v is None or pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):return '-' if v is None or pd.isna(v) else f'{float(v):.{d}f}'


def main():
    x5,coverage=load5_full()
    h1=enrich(resample_full(x5,'1h')); h4=enrich(resample_full(x5,'4h'))
    events,contexts=build_events(x5,h1,h4)
    events.to_csv(OUT_EVENTS,index=False)

    s,champ,gates,champ_trades=strategy_analysis(events,contexts)
    s.to_csv(OUT_SUMMARY,index=False); pd.DataFrame(champ_trades).to_csv(OUT_CHAMP,index=False)
    forensic,stable,tree=forensic_analysis(events); forensic.to_csv(OUT_FORENSIC,index=False)

    label_rates=[]
    for (part,etf,reg),q in events.groupby(['partition','entry_tf','regime']):
        n=len(q); ft=int((q.label=='FOLLOWTHROUGH').sum()); fk=int((q.label=='FAKEOUT').sum()); amb=int((q.label=='AMBIGUOUS').sum())
        label_rates.append({'partition':part,'entry_tf':etf,'regime':reg,'n':n,'followthrough':ft,'fakeout':fk,'ambiguous':amb,
                            'follow_rate_nonamb':ft/(ft+fk) if ft+fk else None})

    payload={'experiment':'B22D_FRESH_4H_FIRST_PULLBACK','data_rows_5m':int(len(x5)),'coverage':float(coverage),
             'event_count':int(len(events)),'strategy_champion':champ,'gates':gates,'label_rates':label_rates,
             'stable_discriminators':stable,'tree':tree}
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+'\n')

    md=['# BTC Fresh 4H Strong Bull → First Pullback B22D — Result','',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'Fresh 4h STRONG activation → first lower-TF healthy pullback/reclaim only → reversal-state exit. Fakeout forensic uses only pre-entry features.','',
        '## Strategy — development leaderboard','',
        '| Entry TF | Regime | Exit | N | WR | PF | Median ret | Median MFE | Median MAE | Hold h | Eligible |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    dev=s[s.partition=='development'].copy(); dev['eligible']=dev.apply(eligible,axis=1); dev=dev.sort_values(['eligible','profit_factor','win_rate'],ascending=[False,False,False])
    for r in dev.itertuples(index=False):
        md.append(f'| {r.entry_tf} | {r.regime} | {r.exit_type} | {r.n} | {pct(r.win_rate)} | {num(r.profit_factor)} | {pct(r.median_return)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {num(r.median_hold_h,1)} | {"YES" if r.eligible else "NO"} |')
    md += ['', '## Strategy replication', '']
    if champ is None: md.append('No development candidate passed the frozen eligibility gates.')
    else:
        md.append(f"Champion: **{champ['entry_tf']} / {champ['regime']} / {champ['exit_type']}**")
        md += ['', '| Partition | N | WR | PF | Median ret | Median MFE | Median MAE |', '|---|---:|---:|---:|---:|---:|---:|']
        for p,m in champ['partitions'].items(): md.append(f"| {p} | {m.get('n',0)} | {pct(m.get('win_rate'))} | {num(m.get('profit_factor'))} | {pct(m.get('median_return'))} | {pct(m.get('median_mfe'))} | {pct(m.get('median_mae'))} |")
        md += ['',f"- B22D_REPLICATED_CLUE: **{'PASS' if gates['B22D_REPLICATED_CLUE'] else 'FAIL'}**",f"- HIGH_PRECISION_CLUE: **{'PASS' if gates['HIGH_PRECISION_CLUE'] else 'FAIL'}**"]

    md += ['', '## Fakeout label rates','', '| Partition | Entry TF | Regime | N | Follow | Fakeout | Ambig | Follow rate (non-amb) |','|---|---|---|---:|---:|---:|---:|---:|']
    for r in label_rates: md.append(f"| {r['partition']} | {r['entry_tf']} | {r['regime']} | {r['n']} | {r['followthrough']} | {r['fakeout']} | {r['ambiguous']} | {pct(r['follow_rate_nonamb'])} |")

    md += ['', '## Stable pre-entry fakeout discriminators','']
    if not stable: md.append('No feature met the frozen cross-partition SMD replication rule.')
    else:
        md.append('| Feature | Dev SMD | External SMD | Ref-val SMD | Dev med Follow | Dev med Fake |')
        md.append('|---|---:|---:|---:|---:|---:|')
        for feat in stable:
            q=forensic[forensic.feature==feat].set_index('partition')
            md.append(f"| {feat} | {num(q.loc['development','smd'])} | {num(q.loc['external','smd'])} | {num(q.loc['reference_validation','smd'])} | {num(q.loc['development','median_follow'],4)} | {num(q.loc['development','median_fake'],4)} |")

    md += ['', '## Shallow fakeout tree (development-only)','']
    if tree is None: md.append('Tree not fit / no eligible leaf.')
    else:
        md.append('```text'); md.extend(tree['rule_text'].rstrip().splitlines()); md.append('```')
        md += ['', '| Partition | Selected N | Follow rate | Baseline | Lift |','|---|---:|---:|---:|---:|']
        for p,m in tree['partitions'].items(): md.append(f"| {p} | {m['n']} | {pct(m['follow_rate'])} | {pct(m['baseline_rate'])} | {pct(m['lift'])} |")
        md.append('')
        md.append('Tree is forensic only; it is not a promoted trading filter in B22D.')

    md += ['', '## Causality / interpretation','',
           '- All 1h/4h states are shifted to candle-close availability before use.',
           '- Aggregate taker flow is kline-level flow, not L2/order-book evidence.',
           '- August 2026 is diagnostic only.',
           '- Live BBC remains untouched.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print(json.dumps(payload,indent=2,default=str))


if __name__=='__main__':
    main()
