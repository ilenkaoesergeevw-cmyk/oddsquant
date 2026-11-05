import "dotenv/config";

import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Mistral } from "@mistralai/mistralai";
import type { ChatCompletionRequest } from "@mistralai/mistralai/models/components";

const MODEL = "mistral-small-latest";
const MAX_MESSAGES = 50;
const MAX_CONTENT_CHARS = 4000;
const PORT = Number(process.env.PORT ?? 3000);

const apiKey = process.env.MISTRAL_API_KEY;
if (!apiKey) {
  console.error("Error: MISTRAL_API_KEY is not set.");
  console.error("Copy .env.example to .env and fill it in, or run: export MISTRAL_API_KEY=...");
  process.exit(1);
}

const mistral = new Mistral({ apiKey });

const app = express();
app.use(express.json({ limit: "256kb" }));

const publicDir = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public");
app.use(express.static(publicDir));

type Messages = ChatCompletionRequest["messages"];

function contentToText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((chunk) =>
        chunk && typeof chunk === "object" && typeof (chunk as { text?: unknown }).text === "string"
          ? (chunk as { text: string }).text
          : "",
      )
      .join("");
  }
  return "";
}

app.post("/api/chat", async (req, res) => {
  const raw = req.body?.messages;

  if (!Array.isArray(raw) || raw.length === 0) {
    res.status(400).json({ error: "`messages` must be a non-empty array of { role, content }" });
    return;
  }

  const messages: Messages = [];
  for (const m of raw.slice(-MAX_MESSAGES)) {
    if (!m || typeof m !== "object") {
      res.status(400).json({ error: "Each message must be an object with role and content" });
      return;
    }
    const { role, content } = m as { role?: unknown; content?: unknown };
    if (typeof content !== "string" || content.trim().length === 0) {
      res.status(400).json({ error: "Each message must have a non-empty string `content`" });
      return;
    }
    const trimmed = content.slice(0, MAX_CONTENT_CHARS);
    if (role === "user") {
      messages.push({ role, content: trimmed });
    } else if (role === "assistant") {
      messages.push({ role, content: trimmed });
    } else if (role === "system") {
      messages.push({ role, content: trimmed });
    } else {
      res.status(400).json({ error: "`role` must be 'user', 'assistant' or 'system'" });
      return;
    }
  }

  try {
    const result = await mistral.chat.complete({ model: MODEL, messages });
    res.json({ reply: contentToText(result.choices[0]?.message?.content) });
  } catch (err) {
    console.error("Mistral API error:", err instanceof Error ? err.message : err);
    res.status(502).json({ error: "The Mistral API request failed. Check the server logs." });
  }
});

app.listen(PORT, () => {
  console.log(`Chat app running at http://localhost:${PORT} (model: ${MODEL})`);
});
