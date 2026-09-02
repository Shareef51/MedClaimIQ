from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_fhir_model_endpoint_is_public_and_documents_boundary():
    response = client.get('/api/v1/healthcare-fhir-model')
    assert response.status_code == 200
    body = response.json()
    assert 'Patient' in body['resources']
    assert 'ExplanationOfBenefit' in body['resources']
    assert body['events']['topic'] == 'medclaimiq.healthcare.events.v1'


def test_mock_hospital_capability_statement_is_r4():
    response = client.get('/mock-fhir/metadata')
    assert response.status_code == 200
    body = response.json()
    assert body['resourceType'] == 'CapabilityStatement'
    assert body['fhirVersion'] == '4.0.1'


def test_mock_hospital_read_and_vread_emit_version_etag():
    current = client.get('/mock-fhir/Patient/patient-001')
    assert current.status_code == 200
    assert current.json()['meta']['versionId'] == '2'
    assert current.headers['etag'] == 'W/"2"'
    historical = client.get('/mock-fhir/Patient/patient-001/_history/2')
    assert historical.status_code == 200
    assert historical.json()['id'] == 'patient-001'


def test_mock_hospital_patient_filter_and_bundle_shape():
    response = client.get('/mock-fhir/Encounter', params={'patient':'patient-001','_count':1})
    body = response.json()
    assert body['resourceType'] == 'Bundle'
    assert body['type'] == 'searchset'
    assert body['total'] == 1
    assert body['entry'][0]['resource']['subject']['reference'] == 'Patient/patient-001'
