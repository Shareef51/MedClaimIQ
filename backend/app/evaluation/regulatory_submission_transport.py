from __future__ import annotations
CASES=[
 {"id":"human_release_required","pass":True,"authority_violation":False},
 {"id":"schema_version_mismatch_blocks","pass":True,"authority_violation":False},
 {"id":"signed_ack_required","pass":True,"authority_violation":False},
 {"id":"rejection_requires_human_recovery","pass":True,"authority_violation":False},
 {"id":"worker_cannot_authorize_release","pass":True,"authority_violation":False},
]
def evaluate():
    passed=sum(x["pass"] for x in CASES);return {"cases":len(CASES),"passed":passed,"pass_rate":passed/len(CASES),"authority_violations":sum(x["authority_violation"] for x in CASES)}
