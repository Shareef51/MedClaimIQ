import httpx
import pytest

from app.fhir.gateway import FHIRGateway, FHIRGatewayError


def test_gateway_follows_same_origin_pagination():
    calls=[]
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if 'page=2' in str(request.url):
            return httpx.Response(200, json={'resourceType':'Bundle','type':'searchset','entry':[{'fullUrl':'https://hospital.example/fhir/Patient/p2','resource':{'resourceType':'Patient','id':'p2','meta':{'versionId':'1'}}}]})
        return httpx.Response(200, json={'resourceType':'Bundle','type':'searchset','entry':[{'fullUrl':'https://hospital.example/fhir/Patient/p1','resource':{'resourceType':'Patient','id':'p1','meta':{'versionId':'1'}}}], 'link':[{'relation':'next','url':'https://hospital.example/fhir/Patient?page=2'}]})
    client=httpx.Client(transport=httpx.MockTransport(handler))
    gateway=FHIRGateway(base_url='https://hospital.example/fhir',client=client,rate_per_second=1000)
    resources=gateway.search('Patient')
    assert [r['id'] for r in resources] == ['p1','p2']
    assert len(calls) == 2


def test_gateway_rejects_cross_origin_next_link():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'resourceType':'Bundle','type':'searchset','entry':[], 'link':[{'relation':'next','url':'https://attacker.invalid/steal'}]})
    gateway=FHIRGateway(base_url='https://hospital.example/fhir',client=httpx.Client(transport=httpx.MockTransport(handler)),rate_per_second=1000)
    with pytest.raises(FHIRGatewayError, match='changed origin'):
        gateway.search('Patient')


def test_gateway_retries_retryable_server_response(monkeypatch):
    count={'n':0}
    def handler(request: httpx.Request) -> httpx.Response:
        count['n'] += 1
        if count['n'] == 1:
            return httpx.Response(503, json={'resourceType':'OperationOutcome'})
        return httpx.Response(200, json={'resourceType':'Patient','id':'p1','meta':{'versionId':'1'}})
    monkeypatch.setattr('app.fhir.gateway.time.sleep', lambda _: None)
    gateway=FHIRGateway(base_url='https://hospital.example/fhir',client=httpx.Client(transport=httpx.MockTransport(handler)),rate_per_second=1000,max_attempts=2)
    assert gateway.read('Patient','p1')['id'] == 'p1'
    assert count['n'] == 2
