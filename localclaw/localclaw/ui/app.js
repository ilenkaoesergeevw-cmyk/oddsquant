const TOKEN = window.LC_TOKEN;
const state = { sessions: [], current: null, providers: [], activeProvider: null, skills: [], pending: [] };

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "X-LC-Token": TOKEN, "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

const PATH_RE = /(?:[A-Za-z]:\\|\/(?:home|Users|root|tmp|workspace))[^\s"'<>]*?(?:\.(?:py|js|ts|md|txt|json|html|css|docx|pptx|xlsx|png|jpg|jpeg|mp4|zip|csv|yaml|yml|toml|xml|sh|bat|exe))/g;

function linkify(text) {
  let html = esc(text);
  return html.replace(PATH_RE, m => `<span class="path-link" data-path="${m}">${m}</span>`);
}

function renderAttachment(a) {
  const url = `/api/attachment?path=${encodeURIComponent(a.path)}&token=${TOKEN}`;
  if (a.kind === "image") return `<img class="attachment" src="${url}" alt="${esc(a.name)}">`;
  if (a.kind === "video") return `<video class="attachment" controls src="${url}"></video>`;
  return `<span class="file-chip">📄 <span class="path-link" data-path="${esc(a.path)}">${esc(a.name)}</span></span>`;
}

function renderMessage(m) {
  const div = document.createElement("div");
  div.className = "msg " + m.role;
  let html = linkify(m.content || "");
  if (m.attachments && m.attachments.length) {
    html += "<div>" + m.attachments.map(renderAttachment).join("") + "</div>";
  }
  div.innerHTML = html;
  return div;
}

async function loadSessions() {
  const data = await api("/api/sessions");
  state.sessions = data.sessions;
  const box = document.getElementById("sessions");
  box.innerHTML = "";
  for (const s of state.sessions) {
    const el = document.createElement("div");
    el.className = "session" + (state.current === s.id ? " active" : "");
    el.textContent = (s.title || "新任务") + (s.project ? " 📁" : "");
    el.onclick = () => selectSession(s.id);
    box.appendChild(el);
  }
}

async function selectSession(id) {
  state.current = id;
  await loadSessions();
  const data = await api("/api/messages?session_id=" + id);
  const chat = document.getElementById("chat");
  chat.innerHTML = "";
  for (const m of data.messages) chat.appendChild(renderMessage(m));
  chat.scrollTop = chat.scrollHeight;
  document.querySelectorAll(".path-link").forEach(el => {
    el.onclick = async () => {
      try { await api("/api/files/reveal", { method: "POST", body: JSON.stringify({ path: el.dataset.path }) }); }
      catch (e) { alert(e.message); }
    };
  });
}

async function loadProviders() {
  const data = await api("/api/providers");
  state.providers = data.providers;
  const box = document.getElementById("providers");
  box.innerHTML = "";
  if (!state.providers.length) {
    box.innerHTML = '<div style="font-size:12px;color:#8b93a7">把模型文件夹放入 models/ 后点击“刷新”</div>';
    return;
  }
  for (const p of state.providers) {
    const el = document.createElement("div");
    el.className = "provider" + (state.activeProvider === p.id ? " active" : "");
    el.innerHTML = `<span>${esc(p.label)}</span>${p.ready ? "" : '<span class="not-ready">未找到可执行文件</span>'}`;
    el.onclick = () => { state.activeProvider = p.id; loadProviders(); };
    box.appendChild(el);
  }
}

async function loadSkills() {
  const data = await api("/api/skills");
  state.skills = data.skills;
  const box = document.getElementById("skills");
  box.innerHTML = "";
  for (const s of state.skills) {
    const el = document.createElement("div");
    el.className = "skill";
    el.innerHTML = `<label title="${esc(s.description)}"><input type="checkbox" ${s.enabled ? "checked" : ""} data-name="${esc(s.name)}"> ${esc(s.name)}</label>`;
    box.appendChild(el);
  }
  box.querySelectorAll("input[type=checkbox]").forEach(cb => {
    cb.onchange = () => api("/api/skills/toggle", { method: "POST", body: JSON.stringify({ name: cb.dataset.name, enabled: cb.checked }) });
  });
}

async function loadConfig() {
  const data = await api("/api/config");
  document.getElementById("inp-roots").value = (data.config.allowed_roots || []).join("\n");
}

function addPending(a) {
  state.pending.push(a);
  const box = document.getElementById("pending-attachments");
  const chip = document.createElement("span");
  chip.className = "chip";
  chip.textContent = (a.kind === "image" ? "🖼 " : a.kind === "video" ? "🎬 " : "📄 ") + a.name + " ";
  const rm = document.createElement("button");
  rm.textContent = "✕";
  rm.onclick = () => { state.pending = state.pending.filter(x => x !== a); box.removeChild(chip); };
  chip.appendChild(rm);
  box.appendChild(chip);
}

async function uploadFile(file) {
  const buf = await file.arrayBuffer();
  let bin = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
  const data = await api("/api/upload", {
    method: "POST",
    body: JSON.stringify({ session_id: state.current || "misc", filename: file.name, data_base64: btoa(bin) }),
  });
  addPending(data);
}

async function send() {
  const input = document.getElementById("input");
  const message = input.value.trim();
  if (!message && !state.pending.length) return;
  input.value = "";
  const attachments = state.pending.slice();
  state.pending = [];
  document.getElementById("pending-attachments").innerHTML = "";
  const chat = document.getElementById("chat");
  const um = document.createElement("div");
  um.className = "msg user";
  um.innerHTML = esc(message) + (attachments.length ? "<div>" + attachments.map(renderAttachment).join("") + "</div>" : "");
  chat.appendChild(um);
  chat.scrollTop = chat.scrollHeight;
  try {
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: state.current,
        project: document.getElementById("inp-project").value.trim(),
        message,
        provider: state.activeProvider,
        attachments,
      }),
    });
    state.current = res.session_id;
    const am = document.createElement("div");
    am.className = "msg assistant";
    am.innerHTML = linkify(res.reply || res.error || "") + `<div class="meta">模型: ${esc(res.provider || "无")}</div>`;
    chat.appendChild(am);
    chat.querySelectorAll(".path-link").forEach(el => {
      el.onclick = async () => {
        try { await api("/api/files/reveal", { method: "POST", body: JSON.stringify({ path: el.dataset.path }) }); }
        catch (e) { alert(e.message); }
      };
    });
    chat.scrollTop = chat.scrollHeight;
    await loadSessions();
  } catch (e) {
    const am = document.createElement("div");
    am.className = "msg assistant";
    am.textContent = "出错: " + e.message;
    chat.appendChild(am);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSessions(); await loadProviders(); await loadSkills(); await loadConfig();
  document.getElementById("btn-new").onclick = async () => {
    const r = await api("/api/session", { method: "POST", body: JSON.stringify({ title: "新任务", project: document.getElementById("inp-project").value.trim() }) });
    await selectSession(r.id);
  };
  document.getElementById("btn-refresh-models").onclick = loadProviders;
  document.getElementById("btn-refresh-skills").onclick = loadSkills;
  document.getElementById("btn-send").onclick = send;
  document.getElementById("input").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  document.getElementById("btn-attach").onclick = () => document.getElementById("file-input").click();
  document.getElementById("file-input").onchange = async e => {
    for (const f of e.target.files) await uploadFile(f);
    e.target.value = "";
  };
  document.getElementById("btn-shot").onclick = async () => {
    const r = await api("/api/screenshot", { method: "POST", body: "{}" });
    addPending({ path: r.path, name: r.path.split(/[\\/]/).pop(), kind: "image" });
  };
  document.getElementById("btn-zip").onclick = async () => {
    const p = prompt("要打包为 ZIP 的目录路径：", document.getElementById("inp-project").value.trim());
    if (!p) return;
    try {
      const r = await api("/api/zip", { method: "POST", body: JSON.stringify({ path: p }) });
      alert("已打包: " + r.zip + " (" + r.size + " 字节)\n可在资源管理器中打开该路径查看。");
      await api("/api/files/reveal", { method: "POST", body: JSON.stringify({ path: r.zip }) });
    } catch (e) { alert(e.message); }
  };
  document.getElementById("btn-office").onclick = () => document.getElementById("office-panel").classList.toggle("hidden");
  document.getElementById("btn-office-run").onclick = async () => {
    const app = document.getElementById("office-app").value;
    const path = document.getElementById("office-path").value.trim();
    const text = document.getElementById("office-text").value;
    try {
      const body = app === "word"
        ? { app, action: "create", path, text }
        : { app, path, slides: [{ title: text || "新演示文稿", bullets: [] }] };
      const r = await api("/api/office", { method: "POST", body: JSON.stringify(body) });
      document.getElementById("office-result").textContent = "已生成: " + (r.path || JSON.stringify(r));
    } catch (e) { document.getElementById("office-result").textContent = e.message; }
  };
  document.getElementById("btn-save-config").onclick = async () => {
    const roots = document.getElementById("inp-roots").value.split("\n").map(s => s.trim()).filter(Boolean);
    await api("/api/config", { method: "POST", body: JSON.stringify({ allowed_roots: roots }) });
    alert("已保存");
  };
});
