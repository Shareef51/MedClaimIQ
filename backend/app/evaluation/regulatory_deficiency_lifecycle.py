def evaluate_lifecycle_traceability(investigations, plans, attestations):
    inv_keys={x["deficiency_key"] for x in investigations}; plan_keys={x["deficiency_key"] for x in plans}; att_keys={x["deficiency_key"] for x in attestations}
    complete=inv_keys & plan_keys & att_keys
    return {"investigation_to_attestation_traceability": (len(complete)/len(inv_keys) if inv_keys else 1.0), "untraced_deficiency_count": len(inv_keys-complete)}
