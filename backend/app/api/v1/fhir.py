from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.domain.fhir import FHIR_R4_VERSION, SUPPORTED_RESOURCE_TYPES

router = APIRouter(tags=["healthcare-fhir"])
mock_router = APIRouter(prefix="/mock-fhir", tags=["synthetic-fhir"])


def _resources() -> list[dict[str, object]]:
    return [
        {"resourceType":"Organization","id":"org-hospital-001","meta":{"versionId":"1","lastUpdated":"2026-08-01T09:00:00Z"},"identifier":[{"system":"https://synthetic.medclaimiq.example/org","value":"HOSP-001"}],"name":"Synthetic General Hospital"},
        {"resourceType":"Organization","id":"org-payer-001","meta":{"versionId":"1","lastUpdated":"2026-08-01T09:00:00Z"},"identifier":[{"system":"https://synthetic.medclaimiq.example/payer","value":"PAY-001"}],"name":"Synthetic Health Plan"},
        {"resourceType":"Practitioner","id":"prac-001","meta":{"versionId":"1","lastUpdated":"2026-08-01T09:00:00Z"},"identifier":[{"system":"https://synthetic.medclaimiq.example/practitioner","value":"NPI-SYN-1001"}],"name":[{"family":"Rao","given":["Asha"]}]},
        {"resourceType":"Patient","id":"patient-001","meta":{"versionId":"2","lastUpdated":"2026-08-15T10:30:00Z"},"identifier":[{"system":"https://synthetic.medclaimiq.example/mrn","value":"MRN-SYN-0001"}],"name":[{"family":"Khan","given":["Mira"]}],"birthDate":"1988-04-12"},
        {"resourceType":"Encounter","id":"enc-001","meta":{"versionId":"1","lastUpdated":"2026-08-15T11:00:00Z"},"status":"finished","class":{"system":"http://terminology.hl7.org/CodeSystem/v3-ActCode","code":"AMB"},"subject":{"reference":"Patient/patient-001"},"period":{"start":"2026-08-10T08:30:00Z","end":"2026-08-10T09:15:00Z"},"serviceProvider":{"reference":"Organization/org-hospital-001"},"participant":[{"individual":{"reference":"Practitioner/prac-001"}}]},
        {"resourceType":"Coverage","id":"cov-001","meta":{"versionId":"3","lastUpdated":"2026-08-01T09:00:00Z"},"status":"active","beneficiary":{"reference":"Patient/patient-001"},"subscriberId":"SYN-SUB-001","payor":[{"reference":"Organization/org-payer-001"}],"period":{"start":"2026-01-01","end":"2026-12-31"}},
        {"resourceType":"Claim","id":"fhir-claim-001","meta":{"versionId":"2","lastUpdated":"2026-08-16T12:00:00Z"},"status":"active","type":{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/claim-type","code":"professional"}]},"patient":{"reference":"Patient/patient-001"},"created":"2026-08-10","provider":{"reference":"Organization/org-hospital-001"},"insurer":{"reference":"Organization/org-payer-001"},"insurance":[{"sequence":1,"focal":True,"coverage":{"reference":"Coverage/cov-001"}}],"item":[{"sequence":1,"encounter":[{"reference":"Encounter/enc-001"}],"productOrService":{"coding":[{"system":"http://www.ama-assn.org/go/cpt","code":"99213"}]},"servicedDate":"2026-08-10","unitPrice":{"value":150,"currency":"USD"},"net":{"value":150,"currency":"USD"}}],"total":{"value":150,"currency":"USD"}},
        {"resourceType":"ExplanationOfBenefit","id":"eob-001","meta":{"versionId":"1","lastUpdated":"2026-08-17T14:00:00Z"},"status":"active","type":{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/claim-type","code":"professional"}]},"use":"claim","patient":{"reference":"Patient/patient-001"},"created":"2026-08-10","insurer":{"reference":"Organization/org-payer-001"},"provider":{"reference":"Organization/org-hospital-001"},"outcome":"complete","insurance":[{"focal":True,"coverage":{"reference":"Coverage/cov-001"}}],"item":[{"sequence":1,"encounter":[{"reference":"Encounter/enc-001"}],"productOrService":{"coding":[{"system":"http://www.ama-assn.org/go/cpt","code":"99213"}]},"servicedDate":"2026-08-10"}],"total":[{"category":{"coding":[{"code":"submitted"}]},"amount":{"value":150,"currency":"USD"}}]},
        {"resourceType":"DocumentReference","id":"docref-001","meta":{"versionId":"1","lastUpdated":"2026-08-15T11:05:00Z"},"status":"current","subject":{"reference":"Patient/patient-001"},"date":"2026-08-15T11:05:00Z","author":[{"reference":"Practitioner/prac-001"}],"content":[{"attachment":{"contentType":"application/pdf","url":"https://synthetic.invalid/documents/discharge-001.pdf","title":"Synthetic encounter summary"}}],"context":{"encounter":[{"reference":"Encounter/enc-001"}]}},
    ]


def _matches_patient(resource: dict[str, object], patient_id: str) -> bool:
    target=f"Patient/{patient_id}"
    for key in ("subject","patient","beneficiary"):
        node=resource.get(key)
        if isinstance(node,dict) and node.get("reference")==target: return True
    return resource.get("resourceType")=="Patient" and resource.get("id")==patient_id


@router.get("/healthcare-fhir-model")
def healthcare_fhir_model() -> dict[str, object]:
    return {
        "fhir_release": "R4 / 4.0.1 compatibility boundary",
        "resources": sorted(SUPPORTED_RESOURCE_TYPES),
        "canonicalization": ["validate_resource_identity","capture_meta_version","hash_raw_resource","normalize_to_medclaimiq","persist_provenance"],
        "identity_reconciliation": "Deterministic scoring uses identifiers + demographics; ambiguous matches require review.",
        "gateway": ["SMART_backend_services_ready","pagination","same_origin_next_links","429_5xx_retry","rate_limit","timeouts"],
        "verification": ["hospital_vs_uploaded_claim","field_level_findings","confidence","human_review_on_uncertainty"],
        "events": {"topic":"medclaimiq.healthcare.events.v1","delivery":"transactional_outbox"},
        "safety": "FHIR resources are evidence inputs, not autonomous claim-decision authority.",
    }


@mock_router.get("/metadata")
def mock_metadata(request: Request) -> dict[str, object]:
    return {"resourceType":"CapabilityStatement","id":"medclaimiq-synthetic-hospital","status":"active","date":"2026-08-19","kind":"instance","fhirVersion":FHIR_R4_VERSION,"format":["json","application/fhir+json"],"rest":[{"mode":"server","resource":[{"type":r,"interaction":[{"code":"read"},{"code":"vread"},{"code":"search-type"}]} for r in sorted(SUPPORTED_RESOURCE_TYPES)]}]}


@mock_router.get("/{resource_type}/{logical_id}/_history/{version_id}")
def mock_vread(resource_type: str, logical_id: str, version_id: str) -> JSONResponse:
    for resource in _resources():
        if resource.get("resourceType")==resource_type and resource.get("id")==logical_id and str((resource.get("meta") or {}).get("versionId"))==version_id:
            return JSONResponse(resource, media_type="application/fhir+json", headers={"ETag":f'W/"{version_id}"'})
    raise HTTPException(status_code=404, detail="resource version not found")


@mock_router.get("/{resource_type}/{logical_id}")
def mock_read(resource_type: str, logical_id: str) -> JSONResponse:
    if resource_type not in SUPPORTED_RESOURCE_TYPES: raise HTTPException(status_code=404, detail="unsupported resource")
    for resource in _resources():
        if resource.get("resourceType")==resource_type and resource.get("id")==logical_id:
            version=str((resource.get("meta") or {}).get("versionId") or "1")
            return JSONResponse(resource, media_type="application/fhir+json", headers={"ETag":f'W/"{version}"'})
    raise HTTPException(status_code=404, detail="resource not found")


@mock_router.get("/{resource_type}")
def mock_search(request: Request, resource_type: str, patient: str | None = None, beneficiary: str | None = None, _count: int = Query(2, ge=1, le=50), _page: int = Query(1, ge=1)) -> dict[str, object]:
    if resource_type not in SUPPORTED_RESOURCE_TYPES: raise HTTPException(status_code=404, detail="unsupported resource")
    items=[r for r in _resources() if r.get("resourceType")==resource_type]
    patient_filter=patient or beneficiary
    if patient_filter: items=[r for r in items if _matches_patient(r, patient_filter.replace("Patient/",""))]
    start=(_page-1)*_count; page_items=items[start:start+_count]
    base=str(request.base_url).rstrip("/")
    links=[{"relation":"self","url":str(request.url)}]
    if start+_count < len(items):
        suffix=f"{base}/mock-fhir/{resource_type}?_count={_count}&_page={_page+1}"
        if patient_filter: suffix += f"&patient={patient_filter.replace('Patient/','')}"
        links.append({"relation":"next","url":suffix})
    return {"resourceType":"Bundle","type":"searchset","total":len(items),"link":links,"entry":[{"fullUrl":f"{base}/mock-fhir/{resource_type}/{r['id']}","resource":r} for r in page_items]}
