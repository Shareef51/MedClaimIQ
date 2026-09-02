import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.evaluation.metrics import ndcg_at_k,recall_at_k
raw=json.loads((ROOT/'sample-data/retrieval_ablation_v1.json').read_text());scores={}
for q in raw['queries']:
    for strategy,ranked in q['strategies'].items():
        s=scores.setdefault(strategy,{'recall':[],'ndcg':[]});s['recall'].append(recall_at_k(q['expected'],ranked,3));s['ndcg'].append(ndcg_at_k(q['expected'],ranked,3))
report={k:{'mean_recall_at_3':sum(v['recall'])/len(v['recall']),'mean_ndcg_at_3':sum(v['ndcg'])/len(v['ndcg'])} for k,v in scores.items()};print(json.dumps(report,indent=2))
