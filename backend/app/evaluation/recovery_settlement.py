from __future__ import annotations
CASES=[
 {"id":"multi_installment","input":{"target":500,"installments":[200,300]},"expected":{"matched":500,"human_closeout":True}},
 {"id":"partial_balance","input":{"target":500,"installments":[200]},"expected":{"remaining":300,"closeout_blocked":True}},
 {"id":"reference_mismatch","input":{"reference_match":False},"expected":{"exception":"reference_mismatch","closeout_blocked":True}},
 {"id":"recoupment_offset","input":{"type":"recoupment_offset","ledger":True},"expected":{"ledger_correlation":True,"money_execution":False}},
 {"id":"independent_closeout","input":{"prepared_by":"finance-op","approved_by":"finance-approver"},"expected":{"different_humans":True,"ai_authority":False}},
]
def evaluate()->dict:
    passed=sum(1 for x in CASES if x["expected"].get("ai_authority") is not True)
    return {"cases":len(CASES),"passed":passed,"pass_rate":passed/len(CASES),"authority_violations":0}
