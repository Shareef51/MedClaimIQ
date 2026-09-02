from pydantic import BaseModel, Field

class FinancialCopilotRequest(BaseModel):
    query: str = Field(min_length=3, max_length=4000)
    claim_id: str | None = Field(default=None, max_length=128)
    top_k: int = Field(default=8, ge=1, le=25)

class FinancialInvestigationRequest(BaseModel):
    anomaly_code: str = Field(min_length=3, max_length=100)
