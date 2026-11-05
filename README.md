# Mistral Chat App

Minimal chat web app that calls the Mistral API with the official TypeScript SDK
([`@mistralai/mistralai`](https://www.npmjs.com/package/@mistralai/mistralai)) using the
`mistral-small-latest` model.

`MISTRAL_API_KEY` lives only on the server (`.env` or environment variable) and is never
sent to the browser. The frontend only talks to `POST /api/chat`.

## How it works

- `public/index.html` — static chat UI (vanilla JS), served by the server.
- `src/server.ts` — Express + TypeScript server. `POST /api/chat` accepts
  `{ "messages": [{ "role": "user", "content": "..." }] }`, calls
  `mistral.chat.complete({ model: "mistral-small-latest", messages })` server-side, and
  returns `{ "reply": "..." }`.

## Prerequisites

- Node.js >= 20
- A Mistral API key from <https://console.mistral.ai/api-keys/>

## Install and run locally

```bash
# 1. Install dependencies
npm install

# 2. Add your API key (never commit the .env file)
cp .env.example .env
# edit .env and set: MISTRAL_API_KEY=your_key_here

# 3. Start the dev server (auto-reloads on changes)
npm run dev
# then open http://localhost:3000
```

Alternatively, without a `.env` file:

```bash
export MISTRAL_API_KEY="your_key_here"
npm run dev
```

Other commands:

```bash
npm start          # run without watch mode
npm run typecheck  # TypeScript check (tsc --noEmit)
PORT=8080 npm run dev   # change the port (default: 3000)
```

## API

`POST /api/chat`

Request:

```json
{ "messages": [{ "role": "user", "content": "Hello!" }] }
```

Response:

```json
{ "reply": "Hi! How can I help you today?" }
```

The server validates and truncates the history (last 50 messages, 4000 chars each) before
forwarding it to the Mistral API.
