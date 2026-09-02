from app.fhir.identity import IdentityReconciler
from app.fhir.verification import verify_financial_claim
from app.fhir_canonical import normalize_coverage, normalize_encounter

PATIENT={'resourceType':'Patient','id':'p1','identifier':[{'system':'mrn','value':'MRN-1'}],'name':[{'family':'Khan','given':['Mira']}],'birthDate':'1988-04-12'}


def test_identity_reconciliation_matches_strong_identifier_demographics():
    result=IdentityReconciler().compare({'identifiers':['MRN-1'],'birth_date':'1988-04-12','family_name':'Khan'}, PATIENT)
    assert result.decision == 'matched'
    assert result.score == 1.0


def test_identity_reconciliation_routes_ambiguous_candidate_to_review():
    result=IdentityReconciler().compare({'identifiers':['MRN-1'],'birth_date':'1970-01-01','family_name':'Kha'}, PATIENT)
    assert result.decision == 'review_required'


def test_canonical_encounter_and_coverage_preserve_relationships():
    encounter=normalize_encounter({'resourceType':'Encounter','id':'e1','subject':{'reference':'Patient/p1'},'serviceProvider':{'reference':'Organization/o1'},'period':{'start':'2026-08-10T08:00:00Z'},'status':'finished'})
    coverage=normalize_coverage({'resourceType':'Coverage','id':'c1','beneficiary':{'reference':'Patient/p1'},'payor':[{'reference':'Organization/pay1'}],'subscriberId':'SUB-1','period':{'start':'2026-01-01','end':'2026-12-31'},'status':'active'})
    assert encounter.patient_external_id == 'p1'
    assert encounter.organization_external_id == 'o1'
    assert coverage.payor_external_id == 'pay1'
    assert coverage.subscriber_id == 'SUB-1'


def test_hospital_cross_verification_returns_field_level_match():
    hospital={'resourceType':'Claim','id':'hc1','status':'active','patient':{'reference':'Patient/p1'},'provider':{'reference':'Organization/h1'},'insurer':{'reference':'Organization/pay1'},'created':'2026-08-10','total':{'value':150,'currency':'USD'}}
    result=verify_financial_claim({'patient_external_id':'p1','provider_external_id':'h1','total_amount':'150.00','currency':'USD'}, hospital)
    assert result.status.value == 'match'
    assert result.confidence == 1.0
    assert all(item.status == 'match' for item in result.findings)


def test_hospital_cross_verification_exposes_mismatch_without_deciding_claim():
    hospital={'resourceType':'ExplanationOfBenefit','id':'eob1','status':'active','patient':{'reference':'Patient/p1'},'provider':{'reference':'Organization/h1'},'insurer':{'reference':'Organization/pay1'},'created':'2026-08-10','total':[{'amount':{'value':125,'currency':'USD'}}]}
    result=verify_financial_claim({'patient_external_id':'p1','provider_external_id':'h1','total_amount':'150.00','currency':'USD'}, hospital)
    assert result.status.value == 'partial_match'
    assert any(item.field == 'total_amount' and item.status == 'mismatch' for item in result.findings)


def test_document_reference_organization_and_practitioner_are_canonicalized():
    from app.fhir_canonical import normalize_document_reference, normalize_organization, normalize_practitioner
    doc=normalize_document_reference({'resourceType':'DocumentReference','id':'d1','status':'current','subject':{'reference':'Patient/p1'},'author':[{'reference':'Practitioner/pr1'}],'content':[{'attachment':{'contentType':'application/pdf','url':'https://synthetic.invalid/d.pdf'}}],'context':{'encounter':[{'reference':'Encounter/e1'}]}})
    org=normalize_organization({'resourceType':'Organization','id':'o1','identifier':[{'value':'HOSP-1'}],'name':'Synthetic Hospital','active':True})
    prac=normalize_practitioner({'resourceType':'Practitioner','id':'pr1','identifier':[{'value':'NPI-SYN'}],'name':[{'family':'Rao','given':['Asha']}],'active':True})
    assert doc.patient_external_id == 'p1' and doc.encounter_external_ids == ('e1',)
    assert org.identifier == 'HOSP-1'
    assert prac.family_name == 'Rao' and prac.identifier == 'NPI-SYN'
