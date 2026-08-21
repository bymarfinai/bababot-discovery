#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import btc_orb_b0_baseline as b0
import btc_orb_b1_allhour_4h as b1

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_ORB_B1_H4_Fast_Result.md'
OUT_JSON=ROOT/'BTC_ORB_B1_H4_Fast_Result.json'


def main():
    k=b0.load()
    b=b1.track_b(k)
    results=[]
    for keys,z in b.groupby(['anchor_hour','trigger','geom']):
        ds,vs,ps,pos,ok=b1.gate(z)
        results.append({'anchor_hour':int(keys[0]),'trigger':keys[1],'geom':keys[2],'disc':ds,'val':vs,'pooled':ps,'positive_blocks':pos,'pass70':ok})
    for kind in ['CLASSIC','FAILED_BREAK']:
        for geom in b0.GEOMS:
            z=b[(b.trigger==kind)&(b.geom==geom)]
            ds,vs,ps,pos,ok=b1.gate(z)
            results.append({'anchor_hour':'ALL','trigger':kind,'geom':geom,'disc':ds,'val':vs,'pooled':ps,'positive_blocks':pos,'pass70':ok})
    ranked=sorted(results,key=lambda r:((r['val']['wr'] or 0),(r['val']['exp'] or -9),(r['val']['n'] or 0)),reverse=True)
    cand=[r for r in results if r['pass70']]
    verdict='ROBUST_70_H4_CANDIDATE' if cand else 'NO_ROBUST_70_H4_CANDIDATE'
    out={'protocol':'BTC_ORB_B1_H4_FAST','verdict':verdict,'trade_rows':len(b),'candidates':cand,'top20':ranked[:20]}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    md=['# BTC ORB B1 H4 Fast — Result','',f'**Verdict: {verdict}**','',f'Trade rows: **{len(b):,}**.','','| Hour UTC | Trigger | Geometry | Disc N/WR | Val N/WR | Val Exp | PF | Pass70 |','|---:|---|---|---:|---:|---:|---:|---|']
    for r in ranked[:20]:
        md.append(f"| {r['anchor_hour']} | {r['trigger']} | {r['geom']} | {r['disc']['n']} / {100*r['disc']['wr']:.2f}% | {r['val']['n']} / {100*r['val']['wr']:.2f}% | {100*r['val']['exp']:.3f}% | {r['val']['pf']:.3f} | {r['pass70']} |")
    OUT_MD.write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str))

if __name__=='__main__':
    main()
