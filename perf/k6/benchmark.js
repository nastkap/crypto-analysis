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

const requestTimeout = __ENV.REQUEST_TIMEOUT || (
  payloadBytes > 100000000 ? '900s' :  
  payloadBytes > 50000000 ? '300s' :  
  payloadBytes > 10000000 ? '900s' :   
  '120s'                                
);

const hasRampParams = __ENV.RAMP_UP_1 && __ENV.RAMP_UP_2 && __ENV.RAMP_UP_3;
let scenarios = {};

if (hasRampParams) {
  // SCENARIUSZ S3: Skalowanie
  scenarios.default = {
    executor: 'ramping-vus',
    stages: [
      { duration: __ENV.RAMP_UP_1, target: 1 },     
      { duration: __ENV.RAMP_UP_2, target: 5 },      
      { duration: __ENV.RAMP_UP_3, target: 10 },     
      { duration: __ENV.HOLD || '10s', target: 20 }, 
      { duration: __ENV.RAMP_DOWN || '5s', target: 0 }, 
    ],
    startVUs: 0,
  };
} else {
  // SCENARIUSZ S1/S2/S4/S5: Stała liczba VU
  scenarios.default = {
    executor: 'constant-vus',
    vus: vus,
    duration: duration,
  };
}
export const options = {
  scenarios: scenarios,
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
    timeout: requestTimeout,
    tags: { operation: 'public_key', node: __ENV.NODE_NAME || 'unknown' },
  });
  const body = pkRes.json();
  const extractedKey = body.public_key_pem;
  check(pkRes, {
    'public-key status 200': (r) => r.status === 200,
    'public-key has public_key_pem': () => extractedKey !== undefined && extractedKey !== null,
  });
  if (!extractedKey) {
    throw new Error('Nie udało się pobrać klucza public_key_pem z API!');
  }
  return {
    baseUrl,
    receiverPublicKeyPem: extractedKey,
    message: buildMessage(payloadBytes),
  };
}
export default function (ctx) {
  const tags = { node: __ENV.NODE_NAME || 'unknown' };
  const headers = { 'Content-Type': 'application/json' };
  const timeout = requestTimeout;

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
  const betweenSleep = payloadBytes > 100000000 ? 0.5 : payloadBytes > 50000000 ? 0.3 : 0.1;
  sleep(betweenSleep);

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
  const finalSleep = payloadBytes > 100000000 ? 1.0 : payloadBytes > 50000000 ? 0.5 : Number(__ENV.SLEEP_SECONDS || '0.1');
  sleep(finalSleep);
























}






