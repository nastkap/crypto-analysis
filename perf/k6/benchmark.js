import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

const encDuration = new Trend('encrypt_duration_ms');
const decDuration = new Trend('decrypt_duration_ms');
const decryptMismatchRate = new Rate('decrypt_mismatch_rate');
const completedIterations = new Counter('completed_iterations');

const payloadBytes = Number(__ENV.PAYLOAD_BYTES || '1024');
const vus = Number(__ENV.VUS || (payloadBytes >= 104857600 ? '1' : payloadBytes >= 102400 ? '5' : '20'));
const duration = __ENV.DURATION || '1m';

export const options = {
  vus,
  duration,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<5000'],
    decrypt_mismatch_rate: ['rate==0'],
  },
};

function buildMessage(bytes) {
  return 'A'.repeat(bytes);
}

export function setup() {
  const baseUrl = __ENV.TARGET_URL;
  if (!baseUrl) {
    throw new Error('Missing TARGET_URL environment variable');
  }

  const pkRes = http.get(`${baseUrl}/public-key`, {
    timeout: __ENV.REQUEST_TIMEOUT || '30s',
    tags: { operation: 'public_key', node: __ENV.NODE_NAME || 'unknown' },
  });

  check(pkRes, {
    'public-key status 200': (r) => r.status === 200,
    'public-key has pem': (r) => {
      try {
        return Boolean(r.json('public_key_pem'));
      } catch (_e) {
        return false;
      }
    },
  });

  return {
    baseUrl,
    receiverPublicKeyPem: pkRes.json('public_key_pem'),
    message: buildMessage(payloadBytes),
  };
}

export default function (ctx) {
  const tags = { node: __ENV.NODE_NAME || 'unknown' };
  const headers = { 'Content-Type': 'application/json' };
  const timeout = __ENV.REQUEST_TIMEOUT || '120s';

  const encryptPayload = JSON.stringify({
    message: ctx.message,
    receiver_public_key_pem: ctx.receiverPublicKeyPem,
  });

  const encRes = http.post(`${ctx.baseUrl}/encrypt`, encryptPayload, {
    headers,
    timeout,
    tags: { ...tags, operation: 'encrypt' },
  });

  const encOk = check(encRes, {
    'encrypt status 200': (r) => r.status === 200,
    'encrypt has package': (r) => {
      try {
        return Boolean(r.json('package'));
      } catch (_e) {
        return false;
      }
    },
  });

  if (!encOk) {
    sleep(0.1);
    return;
  }

  encDuration.add(encRes.timings.duration, tags);

  const pkg = encRes.json('package');
  const decryptPayload = JSON.stringify({
    ephemeral_pub_bytes_b64: pkg.ephemeral_pub_bytes_b64,
    nonce_b64: pkg.nonce_b64,
    ciphertext_b64: pkg.ciphertext_b64,
  });

  const decRes = http.post(`${ctx.baseUrl}/decrypt`, decryptPayload, {
    headers,
    timeout,
    tags: { ...tags, operation: 'decrypt' },
  });

  const decOk = check(decRes, {
    'decrypt status 200': (r) => r.status === 200,
    'decrypt has plaintext': (r) => {
      try {
        return typeof r.json('decrypted_message') === 'string';
      } catch (_e) {
        return false;
      }
    },
  });

  if (decOk) {
    decDuration.add(decRes.timings.duration, tags);
    const decryptedMessage = decRes.json('decrypted_message');
    const matches = decryptedMessage === ctx.message;
    decryptMismatchRate.add(matches ? 0 : 1, tags);
    completedIterations.add(1, tags);
  }

  sleep(Number(__ENV.SLEEP_SECONDS || '0.1'));
}
