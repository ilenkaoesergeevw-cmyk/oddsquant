import express from "express";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { WebSocketServer, WebSocket } from "ws";

const PORT = Number(process.env.PORT ?? 8080);
const MAX_PAYLOAD_BYTES = 64 * 1024 * 1024;
const MAX_QUEUED = 5000;

const app = express();
const publicDir = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public");
app.use(express.static(publicDir));

const server = http.createServer(app);
const wss = new WebSocketServer({ server, maxPayload: MAX_PAYLOAD_BYTES });

interface Client {
  ws: WebSocket;
  auth: string;
  name: string;
}

const rooms = new Map<string, Set<Client>>();
const inbox = new Map<string, string[]>();

function peersOf(auth: string): string[] {
  const set = rooms.get(auth);
  return set ? [...set].map((c) => c.name) : [];
}

function broadcastPeers(auth: string): void {
  const set = rooms.get(auth);
  if (!set) return;
  const msg = JSON.stringify({ t: "peers", peers: peersOf(auth) });
  for (const c of set) {
    if (c.ws.readyState === WebSocket.OPEN) c.ws.send(msg);
  }
}

wss.on("connection", (ws) => {
  let me: Client | null = null;

  ws.on("message", (data) => {
    let msg: { t?: unknown; auth?: unknown; name?: unknown; payload?: unknown };
    try {
      msg = JSON.parse(data.toString());
    } catch {
      return;
    }

    if (msg.t === "hello" && typeof msg.auth === "string" && typeof msg.name === "string") {
      const auth = msg.auth.slice(0, 128);
      const name = msg.name.slice(0, 64) || "device";
      me = { ws, auth, name };
      let set = rooms.get(auth);
      if (!set) {
        set = new Set();
        rooms.set(auth, set);
      }
      set.add(me);
      ws.send(JSON.stringify({ t: "peers", peers: peersOf(auth) }));
      const queued = inbox.get(auth) ?? [];
      inbox.delete(auth);
      for (const payload of queued) {
        ws.send(JSON.stringify({ t: "msg", from: "peer", payload }));
      }
      broadcastPeers(auth);
      return;
    }

    if (me && msg.t === "msg" && typeof msg.payload === "string") {
      const set = rooms.get(me.auth);
      if (!set) return;
      let delivered = false;
      for (const c of set) {
        if (c === me) continue;
        if (c.ws.readyState === WebSocket.OPEN) {
          c.ws.send(JSON.stringify({ t: "msg", from: me.name, payload: msg.payload }));
          delivered = true;
        }
      }
      if (!delivered) {
        const q = inbox.get(me.auth) ?? [];
        if (q.length < MAX_QUEUED) {
          q.push(msg.payload);
          inbox.set(me.auth, q);
        }
      }
    }
  });

  ws.on("close", () => {
    if (!me) return;
    const set = rooms.get(me.auth);
    if (set) {
      set.delete(me);
      if (set.size === 0) rooms.delete(me.auth);
    }
    broadcastPeers(me.auth);
  });
});

setInterval(() => {
  for (const ws of wss.clients) {
    if (ws.readyState === WebSocket.OPEN) ws.ping();
  }
}, 30_000);

server.listen(PORT, () => {
  console.log(`e2e-sync relay listening on http://localhost:${PORT}`);
  console.log("Relay only: payloads are end-to-end encrypted, the server never sees plaintext or keys.");
});
