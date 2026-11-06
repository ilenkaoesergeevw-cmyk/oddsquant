# e2e-sync

Single-user, end-to-end encrypted text & file transfer between **your own devices**
(e.g. a PC in the US and a phone in China). Text has no size limit; files/images of any
size are sent in encrypted chunks — the protocol has no size cap.

**Security model:** the server is a dumb relay. It only ever sees and forwards
ciphertext (`v1.<iv>.<ciphertext>` AES-256-GCM envelopes) plus an auth token. The
encryption key is derived from your passphrase **on the device only** (PBKDF2-SHA256,
210k iterations) and is never sent anywhere — not even the passphrase leaves the device.

## Architecture

- `src/server.ts` — Express static host + WebSocket relay (`ws`). Groups connections by
  `authToken = base64(SHA-256(raw AES key))`, relays `msg` payloads between connections
  with the same token, and queues them in memory if the other device is offline.
  It never logs payloads.
- `public/crypto.js` — shared WebCrypto helpers (derive key, auth token, AES-GCM
  encrypt/decrypt envelope). Runs identically in the browser and in Node (used by tests).
- `public/core.js` — protocol: chunked text/file envelopes, send with WebSocket
  backpressure, receiver reassembly. No size limits (1 MiB plaintext chunks).
- `public/index.html` — the UI. Open it on both devices, enter the same passphrase.
- `test/roundtrip.mjs` — end-to-end test on loopback: text roundtrip, 3 MB file roundtrip
  byte-identical, no-plaintext-in-relay check, wrong-passphrase isolation, offline queue.

## Run

```bash
cd e2e-sync
npm install
npm run dev        # or: npm start   (PORT=8080 by default)
```

On Windows you can also just double-click `e2e-sync/start.bat` — it clears the
`NODE_OPTIONS` preload quirk, installs dependencies if needed, and starts the server
(the window stays open thanks to `pause` at the end).

Then open `http://<server-host>:8080` on **both** devices (phone + PC) and enter the
same passphrase — press Enter (or click 连接) and the device **auto-pairs**: the device
name is generated automatically and both sides show the same **pairing code**
(`pairingCode` derived from the key); matching codes confirm you are paired with the
right key. Type text or pick files/images — the other device receives them decrypted,
with progress bars. If the peer is offline, the server queues the ciphertext (in
memory) and delivers it when the peer reconnects.

## Deploying for cross-country use (your own server)

Run the server on any machine you control (your US PC, or a small VPS):

```bash
PORT=8080 npm start
```

For the phone in China to reach it, either expose the port on your PC/router, or put the
server behind a reverse proxy with TLS (Caddy/nginx) and open `https://your-domain`
on the phone — the client automatically uses `wss://` when the page is served over HTTPS.

## Security notes & limitations

- Use a **strong passphrase** (e.g. 6+ random words). The server stores only the auth
  token, but that token allows an *offline* brute-force of a weak passphrase. The key
  itself is never transmitted.
- Always use HTTPS/WSS in real deployments so the auth token is not visible on the wire.
- Single user only: everyone with the passphrase joins the same room.
- The offline queue is in-memory: it is lost if the server restarts, and capped at 5000
  queued messages.
- Very large files are reassembled in browser memory; the protocol has no limit, but
  practical phone-browser RAM does (hundreds of MB is fine; multi-GB video on a phone
  may not be).

## Verify

```bash
npm run typecheck
npm test           # spins up the relay on 127.0.0.1 and runs the roundtrip suite
```
