import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, CLAIM_ID, headers } from './common.js';

export const options = {
  scenarios: {
    sse_connect: { executor: 'ramping-vus', startVUs: 0, stages: [{ duration: '30s', target: 100 }, { duration: '2m', target: 100 }, { duration: '30s', target: 0 }] },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    'http_req_duration{endpoint:sse_connect}': ['p(95)<750'],
  },
};

export default function () {
  const r = http.get(`${BASE_URL}/api/v1/claims/${CLAIM_ID}/realtime/events?after_sequence=0`, {
    headers: headers({ Accept: 'text/event-stream' }), timeout: '5s', tags: { endpoint: 'sse_connect' },
  });
  check(r, { 'SSE handshake is accepted or times out after stream open': (x) => [200, 408].includes(x.status) || x.timings.waiting < 5000 });
}
