from __future__ import annotations
import math
from collections import Counter
from collections.abc import Iterable, Sequence

def safe_div(num:float,den:float)->float:return num/den if den else 0.0
def normalized_text(text:str)->str:return " ".join(str(text).lower().split())
def token_f1(expected:str,observed:str)->float:
    e=normalized_text(expected).split(); o=normalized_text(observed).split()
    if not e and not o:return 1.0
    if not e or not o:return 0.0
    common=sum((Counter(e)&Counter(o)).values()); p=safe_div(common,len(o)); r=safe_div(common,len(e)); return safe_div(2*p*r,p+r)
def field_accuracy(expected:dict[str,object],observed:dict[str,object])->float:
    if not expected:return 1.0
    return safe_div(sum(1 for k,v in expected.items() if observed.get(k)==v),len(expected))
def recall_at_k(expected_ids:Iterable[str],ranked_ids:Sequence[str],k:int)->float:
    e=set(expected_ids); return 1.0 if not e else safe_div(len(e.intersection(ranked_ids[:k])),len(e))
def precision_at_k(expected_ids:Iterable[str],ranked_ids:Sequence[str],k:int)->float:
    r=list(ranked_ids[:k]); e=set(expected_ids)
    if not r:return 1.0 if not e else 0.0
    return safe_div(sum(1 for item in r if item in e),len(r))
def reciprocal_rank(expected_ids:Iterable[str],ranked_ids:Sequence[str])->float:
    e=set(expected_ids)
    for idx,item in enumerate(ranked_ids,1):
        if item in e:return 1.0/idx
    return 0.0
def ndcg_at_k(expected_ids:Iterable[str],ranked_ids:Sequence[str],k:int)->float:
    e=set(expected_ids); dcg=sum(1.0/math.log2(i+2) for i,item in enumerate(ranked_ids[:k]) if item in e); ideal=min(len(e),k); idcg=sum(1.0/math.log2(i+2) for i in range(ideal)); return safe_div(dcg,idcg) if idcg else 1.0
def citation_exactness(expected:Sequence[dict[str,object]],observed:Sequence[dict[str,object]])->float:
    def key(c):return (str(c.get("source_id","")),str(c.get("source_version","")),str(c.get("locator","")),str(c.get("evidence_key","")))
    e={key(c) for c in expected}; o={key(c) for c in observed}
    if not e:return 1.0 if not o else 0.0
    return safe_div(len(e&o),len(e|o))
def unsupported_claim_rate(claims:Sequence[dict[str,object]])->float:
    if not claims:return 0.0
    return safe_div(sum(1 for c in claims if str(c.get("support","")) not in {"supported","fully_supported"}),len(claims))
def percentile(values:Sequence[float],p:float)->float:
    if not values:return 0.0
    ordered=sorted(float(v) for v in values); idx=max(0,min(len(ordered)-1,math.ceil((p/100)*len(ordered))-1)); return ordered[idx]
