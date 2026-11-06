const te = new TextEncoder();
const td = new TextDecoder();
const SALT = te.encode("e2e-sync-v1");
const ITERATIONS = 210_000;

export function b64encode(bytes) {
  let bin = "";
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

export function b64decode(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

export async function deriveKey(passphrase) {
  const baseKey = await crypto.subtle.importKey(
    "raw",
    te.encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: SALT, iterations: ITERATIONS, hash: "SHA-256" },
    baseKey,
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"],
  );
}

export async function authToken(key) {
  const raw = await crypto.subtle.exportKey("raw", key);
  const digest = await crypto.subtle.digest("SHA-256", raw);
  return b64encode(new Uint8Array(digest));
}

export async function encrypt(key, obj) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    te.encode(JSON.stringify(obj)),
  );
  return "v1." + b64encode(iv) + "." + b64encode(new Uint8Array(ct));
}

export async function decrypt(key, envelope) {
  const parts = envelope.split(".");
  if (parts.length !== 3 || parts[0] !== "v1") throw new Error("bad envelope");
  const pt = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: b64decode(parts[1]) },
    key,
    b64decode(parts[2]),
  );
  return JSON.parse(td.decode(pt));
}

export function randomId() {
  return b64encode(crypto.getRandomValues(new Uint8Array(16)));
}

export function pairingCode(token) {
  return token
    .replace(/[^A-Za-z0-9]/g, "")
    .slice(0, 8)
    .toUpperCase()
    .match(/.{1,4}/g)
    .join("-");
}
