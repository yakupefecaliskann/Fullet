// Firebase ID token'larında varsayılan olarak Supabase'in beklediği
// `role: authenticated` custom claim'i bulunmaz; bu olmadan Supabase
// Third-Party Auth (Firebase) entegrasyonu her isteği `anon` rolüyle
// çalıştırır. Bu fonksiyon, girişten hemen sonra istemci tarafından
// çağrılır: gelen Firebase JWT'sini KENDİSİ doğrular (Supabase Edge
// Functions'ın platform-seviyesi verify_jwt kontrolü yalnızca Supabase'in
// kendi native Auth JWT'lerini destekliyor, üçüncü taraf JWT'leri değil —
// bu yüzden bu fonksiyon verify_jwt=false ile deploy edilir), sonra Google
// Identity Toolkit Admin API'sini bir servis hesabı ile çağırıp o
// kullanıcıya `role: authenticated` custom claim'ini kalıcı olarak atar.
// İstemci bundan sonra getIdToken(true) ile token'ı zorla yeniler.
//
// Gerekli secrets (supabase secrets set ile, KODA YAZILMAZ):
//   FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY, FIREBASE_PROJECT_ID

const FIREBASE_JWKS_URL =
  'https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com';

function base64UrlDecode(input: string): Uint8Array {
  const padded = input.replace(/-/g, '+').replace(/_/g, '/');
  const pad = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4));
  const binary = atob(padded + pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function base64UrlDecodeToString(input: string): string {
  return new TextDecoder().decode(base64UrlDecode(input));
}

let cachedJwks: { keys: JsonWebKey[] } | null = null;
let cachedJwksAt = 0;

async function getFirebaseJwks(): Promise<{ keys: JsonWebKey[] }> {
  if (cachedJwks && Date.now() - cachedJwksAt < 6 * 60 * 60 * 1000) {
    return cachedJwks;
  }
  const res = await fetch(FIREBASE_JWKS_URL);
  if (!res.ok) throw new Error(`Failed to fetch Firebase JWKS: ${res.status}`);
  cachedJwks = await res.json();
  cachedJwksAt = Date.now();
  return cachedJwks!;
}

/**
 * Firebase ID token'ının imzasını, issuer'ını, audience'ını ve süresini
 * doğrular; geçerliyse `sub` (Firebase UID) döner.
 * https://firebase.google.com/docs/auth/admin/verify-id-tokens#verify_id_tokens_using_a_third-party_jwt_library
 */
async function verifyFirebaseIdToken(
  idToken: string,
  projectId: string,
): Promise<string> {
  const parts = idToken.split('.');
  if (parts.length !== 3) throw new Error('Malformed JWT');
  const [headerB64, payloadB64, signatureB64] = parts;

  const header = JSON.parse(base64UrlDecodeToString(headerB64));
  const payload = JSON.parse(base64UrlDecodeToString(payloadB64));

  if (header.alg !== 'RS256') throw new Error('Unexpected JWT alg');
  if (payload.iss !== `https://securetoken.google.com/${projectId}`) {
    throw new Error('Unexpected JWT issuer');
  }
  if (payload.aud !== projectId) throw new Error('Unexpected JWT audience');
  const now = Math.floor(Date.now() / 1000);
  if (typeof payload.exp !== 'number' || payload.exp < now) {
    throw new Error('JWT expired');
  }
  if (typeof payload.sub !== 'string' || payload.sub.length === 0) {
    throw new Error('JWT missing sub claim');
  }

  const jwks = await getFirebaseJwks();
  const jwk = jwks.keys.find((k) => (k as { kid?: string }).kid === header.kid);
  if (!jwk) throw new Error('No matching Firebase signing key found');

  const publicKey = await crypto.subtle.importKey(
    'jwk',
    jwk,
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false,
    ['verify'],
  );

  const signedData = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  const signature = base64UrlDecode(signatureB64);
  const valid = await crypto.subtle.verify(
    'RSASSA-PKCS1-v1_5',
    publicKey,
    signature,
    signedData,
  );
  if (!valid) throw new Error('Invalid JWT signature');

  return payload.sub as string;
}

function pemToArrayBuffer(pem: string): ArrayBuffer {
  const cleaned = pem
    .replace(/-----BEGIN PRIVATE KEY-----/, '')
    .replace(/-----END PRIVATE KEY-----/, '')
    .replace(/\s/g, '');
  const binary = atob(cleaned);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

async function getGoogleAccessToken(
  clientEmail: string,
  privateKeyPem: string,
): Promise<string> {
  const key = await crypto.subtle.importKey(
    'pkcs8',
    pemToArrayBuffer(privateKeyPem),
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false,
    ['sign'],
  );

  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'RS256', typ: 'JWT' };
  const claims = {
    iss: clientEmail,
    sub: clientEmail,
    aud: 'https://oauth2.googleapis.com/token',
    scope: 'https://www.googleapis.com/auth/identitytoolkit',
    iat: now,
    exp: now + 3600,
  };
  const enc = (obj: unknown) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const unsigned = `${enc(header)}.${enc(claims)}`;
  const signature = await crypto.subtle.sign(
    'RSASSA-PKCS1-v1_5',
    key,
    new TextEncoder().encode(unsigned),
  );
  const sig = btoa(String.fromCharCode(...new Uint8Array(signature)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  const assertion = `${unsigned}.${sig}`;

  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion,
    }),
  });
  if (!res.ok) {
    throw new Error(`Google token exchange failed: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  return data.access_token as string;
}

Deno.serve(async (req: Request) => {
  try {
    const authHeader = req.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      throw new Error('Missing bearer token');
    }
    const idToken = authHeader.slice('Bearer '.length);

    const clientEmail = Deno.env.get('FIREBASE_CLIENT_EMAIL');
    const privateKey = Deno.env.get('FIREBASE_PRIVATE_KEY')?.replace(/\\n/g, '\n');
    const projectId = Deno.env.get('FIREBASE_PROJECT_ID');
    if (!clientEmail || !privateKey || !projectId) {
      throw new Error('Server missing Firebase service account configuration');
    }

    const uid = await verifyFirebaseIdToken(idToken, projectId);

    const accessToken = await getGoogleAccessToken(clientEmail, privateKey);

    const updateRes = await fetch(
      `https://identitytoolkit.googleapis.com/v1/projects/${projectId}/accounts:update`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          localId: uid,
          customAttributes: JSON.stringify({ role: 'authenticated' }),
        }),
      },
    );
    if (!updateRes.ok) {
      throw new Error(
        `Identity Toolkit update failed: ${updateRes.status} ${await updateRes.text()}`,
      );
    }

    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: String(e) }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
});
