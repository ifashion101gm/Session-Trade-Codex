"""Compact MT5 OOS/cross-asset runner; writes aggregates, not daily traces."""
from __future__ import annotations
from calendar import monthrange
from datetime import date
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from asian_session_backtester import load_mt5, run, trading_days

def metrics(result):
    trades=[t for t in result['trades'] if t.get('friction_r') is not None]
    values=[t['friction_r'] for t in trades]; wins=sum(t['outcome']=='TP5_HIT' for t in trades)
    positive=sum(v for v in values if v>0); negative=-sum(v for v in values if v<0)
    equity=peak=maxdd=0.0
    for value in values: equity+=value; peak=max(peak,equity); maxdd=max(maxdd,peak-equity)
    return {'executed_trades':len(trades),'tp5_wins':wins,
            'win_rate_percent':100*wins/len(trades) if trades else 0,
            'profit_factor':positive/negative if negative else None,
            'max_drawdown_r':maxdd,'gross_r':sum(t['gross_r'] for t in trades),
            'net_r':sum(values),'data_quality_failures':sum(s['status']=='REJECTED_DATA_QUALITY' for s in result['sessions'])}

def evaluate(symbol,start,end):
    bars,source=load_mt5(3,symbol,start,end)
    result=run(bars,source,.2,trading_days(start,end),22,False,18,False,'limit',symbol)
    return metrics(result)

def main():
    output=ROOT/'outputs'/'phase2_validation'; output.mkdir(parents=True,exist_ok=True)
    monthly=[]
    for year,months in ((2022,(11,12)),(2023,tuple(range(1,13)))):
        for month in months:
            start=date(year,month,1); end=date(year,month,monthrange(year,month)[1])
            monthly.append({'year_month':f'{year}-{month:02d}','symbol':'EURUSD',**evaluate('EURUSD',start,end)})
    cross=[]
    for symbol in ('EURUSD','GBPUSD','AUDUSD'):
        cross.append({'symbol':symbol,'window':'2022-10-03 to 2022-12-31',**evaluate(symbol,date(2022,10,3),date(2022,12,31))})
    payload={'monthly':monthly,'cross_asset':cross}
    (output/'phase2_results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps(payload,indent=2))
if __name__=='__main__': main()
