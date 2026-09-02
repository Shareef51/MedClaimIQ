from app.domain.regulatory_post_closure_surveillance import POST_CLOSURE_AUTHORITY
from app.evaluation.regulatory_post_closure_surveillance import evaluate_recurrence_signal,evaluate_traceability
assert POST_CLOSURE_AUTHORITY["ai_can_reopen_finding"] is False
assert evaluate_recurrence_signal({"recurrence_score":.95,"sustainability_decay_score":.8,"control_regression_score":.9,"cross_entity_keys":["US","EU"]})["reopen_candidate"] is True
assert evaluate_traceability({"closed_issue":1,"surveillance_signal":1,"recurrence_evidence":1,"human_reopening":1,"renewed_remediation":1,"revalidation":1})["passed"] is True
print("Release 61 verification passed")
