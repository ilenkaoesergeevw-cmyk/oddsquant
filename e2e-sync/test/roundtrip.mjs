import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import WebSocket from "ws";
import { deriveKey, authToken } from "../public/crypto.js";
import { sendText, sendFile, Inbox } from "../public/core.js";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PORT = 18321;
const url = `ws://127.0.0.1:${PORT}`;

const server = spawn("npx", ["tsx", "src/server.ts"], {
  cwd: root,
  env: { ...process.env, PORT: String(PORT) },
  stdio: ["ignore", "pipe", "pipe"],
  detached: true,
});
const clients = [];
await new Promise((resolve, reject) => {
  server.stdout.on("data", (d) => {
    if (d.toString().includes("listening")) resolve();
  });
  server.stderr.on("data", (d) => process.stderr.write(d));
  server.on("exit", (code) => reject(new Error("server exited early: " + code)));
  setTimeout(() => reject(new Error("server start timeout")), 20000);
});

function makeClient(passphrase, name) {
  const state = { ws: null, key: null, token: null, events: [], rawPayloads: [], peers: [] };
  return (async () => {
    state.key = await deriveKey(passphrase);
    state.token = await authToken(state.key);
    state.inbox = new Inbox(state.key, (ev) => state.events.push(ev));
    state.ws = new WebSocket(url);
    await new Promise((res, rej) => {
      state.ws.on("open", res);
      state.ws.on("error", rej);
    });
    state.ws.on("message", async (data) => {
      const msg = JSON.parse(data.toString());
      if (msg.t === "peers") state.peers = msg.peers;
      if (msg.t === "msg") {
        state.rawPayloads.push(msg.payload);
        await state.inbox.handle(msg.from, msg.payload);
      }
    });
    state.ws.send(JSON.stringify({ t: "hello", auth: state.token, name }));
    clients.push(state);
    return state;
  })();
}

async function waitFor(fn, label, timeout = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const v = fn();
    if (v) return v;
    await new Promise((r) => setTimeout(r, 50));
  }
  throw new Error("timeout waiting for: " + label);
}

try {
  const A = await makeClient("correct horse battery staple", "us-pc");
  const B = await makeClient("correct horse battery staple", "china-phone");
  await waitFor(() => A.peers.length === 2 && B.peers.length === 2, "both peers visible");
  console.log("PASS peers visible:", A.peers.join(", "));

  const secretText = "hello 端对端加密 🔒 secret-12345";
  await sendText(A.key, A.ws, secretText);
  const textEv = await waitFor(() => B.events.find((e) => e.type === "text"), "text event");
  assert.equal(textEv.body, secretText);
  console.log("PASS text roundtrip decrypts to original");

  const fileBytes = randomBytes(3 * 1024 * 1024 + 12345);
  const file = new Blob([fileBytes], { type: "image/png" });
  file.name = "secret-photo.png";
  await sendFile(A.key, A.ws, file);
  const fileEv = await waitFor(() => B.events.find((e) => e.type === "file-done"), "file-done event");
  assert.equal(fileEv.name, "secret-photo.png");
  assert.equal(fileEv.size, fileBytes.length);
  const got = new Uint8Array(await fileEv.blob.arrayBuffer());
  assert.equal(createHash("sha256").update(got).digest("hex"), createHash("sha256").update(fileBytes).digest("hex"));
  console.log("PASS file roundtrip: 3MB+ blob reassembled byte-identical");

  const leaked = B.rawPayloads.some((p) => p.includes("secret-12345") || p.includes("secret-photo.png") || p.includes("hello"));
  assert.equal(leaked, false, "plaintext leaked into relayed payload");
  console.log("PASS relayed payloads contain no plaintext (server sees only ciphertext)");

  const C = await makeClient("wrong passphrase", "intruder");
  await sendText(A.key, A.ws, "another secret 67890");
  await new Promise((r) => setTimeout(r, 500));
  assert.equal(C.events.filter((e) => e.type === "text").length, 0);
  console.log("PASS different passphrase = different room, receives nothing");

  B.ws.close();
  await waitFor(() => A.peers.length === 1, "B gone");
  await sendText(A.key, A.ws, "offline queued message");
  await new Promise((r) => setTimeout(r, 300));
  const B2 = await makeClient("correct horse battery staple", "china-phone");
  const queued = await waitFor(() => B2.events.find((e) => e.type === "text" && e.body === "offline queued message"), "queued delivery");
  assert.ok(queued);
  console.log("PASS offline queue: message delivered when peer reconnects");

  console.log("ALL TESTS PASSED");
  process.exitCode = 0;
} catch (e) {
  console.error("TEST FAILED:", e);
  process.exitCode = 1;
} finally {
  for (const c of clients) {
    try {
      c.ws.terminate();
    } catch {}
  }
  try {
    process.kill(-server.pid, "SIGTERM");
  } catch {
    server.kill();
  }
  process.exit(process.exitCode ?? 0);
}
