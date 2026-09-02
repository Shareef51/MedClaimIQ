import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, TOKEN, TENANT, headers } from './common.js';

export const options = {
  scenarios: {
    reviewer_queue: { executor: 'ramping-arrival-rate', startRate: 5, timeUnit: '1s', preAllocatedVUs: 25, maxVUs: 250,
      stages: [{ target: 20, duration: '1m' }, { target: 50, duration: '3m' }, { target: 20, duration: '1m' }] },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{endpoint:review_queue}': ['p(95)<400'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const r = http.get(`${BASE_URL}/api/v1/review/queue`, { headers: headers(), tags: { endpoint: 'review_queue' } });
  check(r, { 'queue authorized': (x) => [200, 403].includes(x.status), 'no server error': (x) => x.status < 500 });
  sleep(0.2);
}
