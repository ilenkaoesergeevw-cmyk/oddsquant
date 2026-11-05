import { encrypt, decrypt, b64encode, b64decode, randomId } from "./crypto.js";

export const CHUNK_BYTES = 1024 * 1024;
const MAX_TEXT_PART = 1024 * 1024;
const SEND_BUFFER_LIMIT = 8 * 1024 * 1024;

export function sendPayload(ws, payload) {
  return new Promise((resolve, reject) => {
    const trySend = () => {
      if (ws.readyState !== 1) return reject(new Error("socket closed"));
      ws.send(JSON.stringify({ t: "msg", payload }));
      if (ws.bufferedAmount > SEND_BUFFER_LIMIT) {
        const timer = setInterval(() => {
          if (ws.bufferedAmount <= SEND_BUFFER_LIMIT) {
            clearInterval(timer);
            resolve();
          }
        }, 20);
      } else {
        resolve();
      }
    };
    trySend();
  });
}

export async function sendText(key, ws, body) {
  const bytes = new TextEncoder().encode(body);
  const total = Math.max(1, Math.ceil(bytes.length / MAX_TEXT_PART));
  const id = randomId();
  for (let seq = 0; seq < total; seq++) {
    const part = body.slice(seq * MAX_TEXT_PART, (seq + 1) * MAX_TEXT_PART);
    await sendPayload(ws, await encrypt(key, { kind: "text", id, seq, total, data: part }));
  }
}

export async function sendFile(key, ws, file, onProgress) {
  const id = randomId();
  const size = file.size;
  const chunks = Math.max(1, Math.ceil(size / CHUNK_BYTES));
  await sendPayload(
    ws,
    await encrypt(key, {
      kind: "manifest",
      id,
      name: file.name,
      size,
      mime: file.type || "application/octet-stream",
      chunks,
    }),
  );
  for (let seq = 0; seq < chunks; seq++) {
    const slice = file.slice(seq * CHUNK_BYTES, Math.min((seq + 1) * CHUNK_BYTES, size));
    const buf = await slice.arrayBuffer();
    await sendPayload(
      ws,
      await encrypt(key, { kind: "chunk", id, seq, data: b64encode(new Uint8Array(buf)) }),
    );
    if (onProgress) onProgress(seq + 1, chunks);
  }
}

export class Inbox {
  constructor(key, onEvent) {
    this.key = key;
    this.onEvent = onEvent;
    this.texts = new Map();
    this.files = new Map();
  }

  async handle(from, envelope) {
    const msg = await decrypt(this.key, envelope);
    if (msg.kind === "text") {
      let entry = this.texts.get(msg.id);
      if (!entry) {
        entry = { parts: new Array(msg.total), received: 0 };
        this.texts.set(msg.id, entry);
      }
      entry.parts[msg.seq] = msg.data;
      entry.received++;
      if (entry.received === msg.total) {
        this.texts.delete(msg.id);
        this.onEvent({ type: "text", from, body: entry.parts.join("") });
      }
    } else if (msg.kind === "manifest") {
      this.files.set(msg.id, {
        meta: msg,
        parts: new Array(msg.chunks),
        received: 0,
      });
      this.onEvent({ type: "file-start", from, id: msg.id, name: msg.name, size: msg.size, mime: msg.mime });
    } else if (msg.kind === "chunk") {
      const f = this.files.get(msg.id);
      if (!f) return;
      f.parts[msg.seq] = b64decode(msg.data);
      f.received++;
      this.onEvent({
        type: "file-progress",
        from,
        id: msg.id,
        received: f.received,
        total: f.meta.chunks,
      });
      if (f.received === f.meta.chunks) {
        this.files.delete(msg.id);
        const blob = new Blob(f.parts, { type: f.meta.mime });
        if (blob.size !== f.meta.size) throw new Error("size mismatch for " + f.meta.name);
        this.onEvent({ type: "file-done", from, name: f.meta.name, size: blob.size, mime: f.meta.mime, blob });
      }
    }
  }
}
