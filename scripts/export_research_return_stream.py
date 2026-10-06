"""Export the selected full-precision net return stream for metric reproduction."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'results/signal_aware_covariance/signal_aware_covariance_results.csv'
account=json.loads((ROOT/'web/public/data/hypothetical_account_snapshot.json').read_text())
model=account['model']
rows=[]
with source.open() as handle:
    for row in csv.DictReader(handle):
        if row['base_policy']==model['base_policy'] and row['exposure_policy']==model['exposure_policy'] and int(row['model_horizon_days'])==model['horizon_days'] and int(row['rebalance_every_days'])==model['rebalance_every_days']:
            rows.append({'date':row['rebalance_date'],'net_return':float(row['net_return'])})
rows.sort(key=lambda r:r['date'])
if len(rows)!=account['statistics']['rebalances']:
    raise ValueError('Return count does not match account')
growth=math.prod(1+r['net_return'] for r in rows)
annualized=growth**((252/model['rebalance_every_days'])/len(rows))-1
nav=peak=100000.0
drawdown=0.0
for row in rows:
    nav*=1+row['net_return'];peak=max(peak,nav);drawdown=min(drawdown,nav/peak-1)
if abs(annualized-account['statistics']['annualized_net_return'])>1e-10 or abs(drawdown-account['statistics']['max_drawdown'])>1e-10:
    raise ValueError('Published metrics do not reproduce')
payload={'schema_version':'1.0','source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'model':model,'observations':rows,'reproduction':{'starting_nav':100000,'ending_nav':nav,'annualized_net_return':annualized,'maximum_drawdown':drawdown,'annualization':'product(1 + net_return) ** ((252 / rebalance_every_days) / observation_count) - 1'}}
(ROOT/'web/public/data/research_return_stream.json').write_text(json.dumps(payload,indent=2)+'\n')
print('Reproduced annualized return and historical drawdown from',len(rows),'observations')
