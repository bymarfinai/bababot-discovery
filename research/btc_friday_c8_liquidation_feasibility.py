#!/usr/bin/env python3
"""C8 data-only probe: official Binance USD-M historical liquidationSnapshot availability."""
from __future__ import annotations
import io,json,zipfile
from pathlib import Path
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'BTC_Friday_C8_Liquidation_Feasibility.json'
OUT_MD=ROOT/'BTC_Friday_C8_Liquidation_Feasibility.md'
BASE='https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/BTCUSDT'
DATES=['2023-12-08','2024-03-15','2024-08-02','2025-01-24','2025-07-18','2026-01-23','2026-07-24']

def probe(ds):
    url=f'{BASE}/BTCUSDT-liquidationSnapshot-{ds}.zip'
    try:
        r=requests.get(url,timeout=45,headers={'User-Agent':'bababot-c8-probe/1.0'})
        out={'date':ds,'status':r.status_code,'bytes':len(r.content),'exists':r.status_code==200}
        if r.status_code!=200:return out
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names=[n for n in zf.namelist() if n.lower().endswith('.csv')]
            if not names:return {**out,'parse_error':'no csv'}
            with zf.open(names[0]) as fh:df=pd.read_csv(fh)
        out['rows']=len(df);out['columns']=[str(c) for c in df.columns]
        out['sample']=df.head(2).astype(str).to_dict(orient='records')
        return out
    except Exception as e:return {'date':ds,'exists':False,'error':str(e)}

def main():
    rows=[probe(d) for d in DATES];exists=sum(bool(r.get('exists')) for r in rows);usable=[r for r in rows if r.get('exists') and r.get('rows',0)>0]
    out={'protocol':'C8_FEASIBILITY','sample_dates':DATES,'existing_archives':exists,'usable_archives':len(usable),'probes':rows,'verdict':'C8_LIQUIDATION_DATA_USABLE' if len(usable)>=5 else 'C8_LIQUIDATION_DATA_INSUFFICIENT'}
    OUT.write_text(json.dumps(out,indent=2,default=str)+'\n')
    md=['# BTC Friday C8 — Liquidation Archive Feasibility','',f"**Verdict: {out['verdict']}**",'',f"Probe dates: **{len(DATES)}**; existing archives: **{exists}**; usable: **{len(usable)}**.",'','| Date | Exists | Rows | Status |','|---|---:|---:|---:|']
    for r in rows:md.append(f"| {r['date']} | {'YES' if r.get('exists') else 'NO'} | {r.get('rows','-')} | {r.get('status','-')} |")
    if usable:md+=['','First usable columns: `'+', '.join(usable[0].get('columns',[]))+'`.']
    md+=['','Data feasibility only. No strategy rule or result inferred here.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
