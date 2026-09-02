import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, CLAIM_ID, headers } from './common.js';

export const options = {
  scenarios: {
    ai_reads: { executor: 'constant-arrival-rate', rate: 5, timeUnit: '1s', duration: '3m', preAllocatedVUs: 20, maxVUs: 100 },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    'http_req_duration{endpoint:rag}': ['p(95)<1800'],
    'http_req_duration{endpoint:mcp}': ['p(95)<700'],
  },
};

export default function () {
  const rag = http.post(`${BASE_URL}/api/v1/claims/${CLAIM_ID}/rag/hybrid-search`, JSON.stringify({ query: 'synthetic claim evidence', top_k: 5 }), { headers: headers(), tags: { endpoint: 'rag' } });
  check(rag, { 'rag no 5xx': (r) => r.status < 500 });
  const mcp = http.get(`${BASE_URL}/api/v1/mcp/tools`, { headers: headers(), tags: { endpoint: 'mcp' } });
  check(mcp, { 'mcp no 5xx': (r) => r.status < 500 });
  sleep(0.5);
}
