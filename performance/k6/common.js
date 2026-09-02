import http from 'k6/http';
import { check } from 'k6';

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
export const TOKEN = __ENV.ACCESS_TOKEN || '';
export const TENANT = __ENV.TENANT_ID || 'tenant-synthetic';
export const CLAIM_ID = __ENV.CLAIM_ID || 'claim-synthetic';

export function headers(extra = {}) {
  return {
    Authorization: `Bearer ${TOKEN}`,
    'X-Tenant-Id': TENANT,
    'Content-Type': 'application/json',
    ...extra,
  };
}

export function checkedGet(path, name) {
  const response = http.get(`${BASE_URL}${path}`, { headers: headers(), tags: { endpoint: name } });
  check(response, { [`${name} status < 500`]: (r) => r.status < 500 });
  return response;
}
