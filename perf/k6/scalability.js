import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const payloadBytes = Number(__ENV.PAYLOAD_BYTES || '102400');
const mismatchRate = new Rate('decrypt_mismatch_rate');
const roundTripDuration = new Trend('round_trip_duration_ms');

export const options = {
  scenarios: {
    ramp_test: {
      executor: 'ramping-vus',
      startVUs: Number(__ENV.START_VUS || '1'),
      stages: [
        { duration: __ENV.RAMP_UP_1 || '1m', target: Number(__ENV.TARGET_VUS_1 || '5') },
        { duration: __ENV.RAMP_UP_2 || '1m', target: Number(__ENV.TARGET_VUS_2 || '15') },
        { duration: __ENV.RAMP_UP_3 || '1m', target: Number(__ENV.TARGET_VUS_3 || '30') },
        { duration: __ENV.HOLD || '1m', target: Number(__ENV.TARGET_VUS_3 || '30') },
        { duration: __ENV.RAMP_DOWN || '30s', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<10000'],
    decrypt_mismatch_rate: ['rate==0'],
    round_trip_duration_ms: ['p(95)<12000'],
  },
};

function payloadText(size) {
  return 'B'.repeat(size);
}

export function setup() {
  const baseUrl = __ENV.TARGET_URL;
  if (!baseUrl) {
    throw new Error('Missing TARGET_URL environment variable');
  }

  const pkRes = http.get(`${baseUrl}/public-key`, { timeout: __ENV.REQUEST_TIMEOUT || '30s' });
  check(pkRes, {
    'public-key status 200': (r) => r.status === 200,
  });

  return {
    baseUrl,
    receiverPublicKeyPem: pkRes.json('public_key_pem'),
    message: payloadText(payloadBytes),
  };
}

export default function (ctx) {
  const headers = { 'Content-Type': 'application/json' };
  const timeout = __ENV.REQUEST_TIMEOUT || '120s';

  const t0 = Date.now();
  const encRes = http.post(
    `${ctx.baseUrl}/encrypt`,
    JSON.stringify({
      message: ctx.message,
      receiver_public_key_pem: ctx.receiverPublicKeyPem,
    }),
    { headers, timeout }
  );

  const encOk = check(encRes, {
    'encrypt status 200': (r) => r.status === 200,
  });

  if (!encOk) {
    sleep(0.1);
    return;
  }

  const pkg = encRes.json('package');
  const decRes = http.post(
    `${ctx.baseUrl}/decrypt`,
    JSON.stringify({
      ephemeral_pub_bytes_b64: pkg.ephemeral_pub_bytes_b64,
      nonce_b64: pkg.nonce_b64,
      ciphertext_b64: pkg.ciphertext_b64,
    }),
    { headers, timeout }
  );

  const decOk = check(decRes, {
    'decrypt status 200': (r) => r.status === 200,
  });

  if (decOk) {
    const decrypted = decRes.json('decrypted_message');
    mismatchRate.add(decrypted === ctx.message ? 0 : 1);
    roundTripDuration.add(Date.now() - t0);
  }

  sleep(Number(__ENV.SLEEP_SECONDS || '0.1'));
}
