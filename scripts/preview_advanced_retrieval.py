from app.rag.query_intelligence import DeterministicQueryPlanner
from app.sparse.provider import HashedBM25SparseEncoder

query = "Does CPT 99213 require prior authorization under the policy active on 2026-08-10?"
plan = DeterministicQueryPlanner().plan(query)
sparse = HashedBM25SparseEncoder().encode_one(query)
print({
    "normalized_query": plan.normalized_query,
    "domains": [item.value for item in plan.domains],
    "variants": list(plan.variants),
    "subqueries": list(plan.subqueries),
    "exact_terms": list(plan.exact_terms),
    "service_date_from": plan.service_date_from.isoformat() if plan.service_date_from else None,
    "service_date_to": plan.service_date_to.isoformat() if plan.service_date_to else None,
    "sparse_non_zero_terms": len(sparse.indices),
    "fallbacks": list(plan.fallbacks),
})
