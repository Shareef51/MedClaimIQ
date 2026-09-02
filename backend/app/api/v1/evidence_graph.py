from fastapi import APIRouter

from app.services.evidence_graph import graph_model_contract

router = APIRouter(tags=["evidence-graph"])


@router.get("/evidence-graph-model")
def evidence_graph_model() -> dict[str, object]:
    return graph_model_contract()
