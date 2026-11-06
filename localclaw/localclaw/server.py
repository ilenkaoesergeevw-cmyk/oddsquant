import base64
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import agent, config, memory
from .providers import scan as scan_providers
from .skills import loader as skills_loader
from .tools import archive, files as filetools
from .tools import office, screenshot as shot
from .tools import shell as shelltools

UI_DIR = Path(__file__).resolve().parent / "ui"
MAX_BODY = 100 * 1024 * 1024


def make_handler(cfg):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LocalClaw/0.1"
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _authorized(self):
            if self.headers.get("X-LC-Token") != cfg["token"]:
                return False
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost", "[::1]")

        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, data, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("请求体过大")
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw or b"{}")

        def _guard(self):
            if self.path == "/api/health":
                return True
            return self._authorized()

        def do_GET(self):
            try:
                u = urlparse(self.path)
                path, q = u.path, parse_qs(u.query)
                if path in ("/", "/index.html"):
                    html = (UI_DIR / "index.html").read_text(encoding="utf-8")
                    self._send_bytes(html.replace("__LC_TOKEN__", cfg["token"]).encode("utf-8"), "text/html; charset=utf-8")
                    return
                if path.startswith("/static/"):
                    f = UI_DIR / path[len("/static/"):]
                    if not f.is_file() or f.parent != UI_DIR:
                        self._json({"error": "not found"}, 404)
                        return
                    ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
                    self._send_bytes(f.read_bytes(), ctype)
                    return
                if path == "/api/attachment":
                    tok = q.get("token", [""])[0]
                    if tok != cfg["token"] and self.headers.get("X-LC-Token") != cfg["token"]:
                        self._json({"error": "unauthorized"}, 401)
                        return
                    ap = Path(q.get("path", [""])[0]).resolve()
                    base = Path(cfg["sessions_dir"]).resolve()
                    if ap != base and base not in ap.parents:
                        self._json({"error": "forbidden"}, 403)
                        return
                    if not ap.is_file():
                        self._json({"error": "not found"}, 404)
                        return
                    ctype = mimetypes.guess_type(str(ap))[0] or "application/octet-stream"
                    self._send_bytes(ap.read_bytes(), ctype)
                    return
                if not self._guard():
                    self._json({"error": "unauthorized"}, 401)
                    return
                if path == "/api/health":
                    self._json({"ok": True})
                elif path == "/api/sessions":
                    self._json({"sessions": memory.list_sessions()})
                elif path == "/api/messages":
                    self._json({"messages": memory.messages(q.get("session_id", [""])[0])})
                elif path == "/api/providers":
                    self._json({"providers": scan_providers(cfg["models_dir"])})
                elif path == "/api/skills":
                    skills = skills_loader.scan(cfg["skills_dirs"])
                    disabled = set(cfg.get("disabled_skills", []))
                    self._json({"skills": [{**s.__dict__, "enabled": s.name not in disabled} for s in skills]})
                elif path == "/api/config":
                    self._json({"config": config.public(cfg)})
                elif path == "/api/memory":
                    project = q.get("project", [""])[0]
                    self._json({"memory": memory.mem_all(project)})
                else:
                    self._json({"error": "not found"}, 404)
            except BrokenPipeError:
                pass
            except Exception as e:
                try:
                    self._json({"error": str(e)}, 500)
                except Exception:
                    pass

        def do_POST(self):
            try:
                u = urlparse(self.path)
                path = u.path
                if not self._guard():
                    self._json({"error": "unauthorized"}, 401)
                    return
                data = self._body()
                if path == "/api/session":
                    sid = memory.new_session(data.get("title", "新任务"), data.get("project", ""))
                    self._json({"id": sid})
                elif path == "/api/session/delete":
                    memory.delete_session(data.get("id", ""))
                    self._json({"ok": True})
                elif path == "/api/session/project":
                    memory.set_project(data.get("id", ""), data.get("project", ""))
                    self._json({"ok": True})
                elif path == "/api/chat":
                    self._json(agent.chat(
                        cfg,
                        session_id=data.get("session_id"),
                        title=data.get("title", ""),
                        project=data.get("project", ""),
                        message=data.get("message", ""),
                        provider_id=data.get("provider"),
                        attachments=data.get("attachments"),
                        skill_names=data.get("skills"),
                    ))
                elif path == "/api/providers/refresh":
                    self._json({"providers": scan_providers(cfg["models_dir"])})
                elif path == "/api/skills/refresh":
                    skills = skills_loader.scan(cfg["skills_dirs"])
                    disabled = set(cfg.get("disabled_skills", []))
                    self._json({"skills": [{**s.__dict__, "enabled": s.name not in disabled} for s in skills]})
                elif path == "/api/skills/toggle":
                    disabled = set(cfg.get("disabled_skills", []))
                    name = data.get("name", "")
                    if data.get("enabled", True):
                        disabled.discard(name)
                    else:
                        disabled.add(name)
                    cfg["disabled_skills"] = sorted(disabled)
                    config.save(cfg)
                    self._json({"ok": True, "disabled_skills": cfg["disabled_skills"]})
                elif path == "/api/upload":
                    sid = data.get("session_id") or "misc"
                    folder = Path(cfg["sessions_dir"]) / sid / "attachments"
                    folder.mkdir(parents=True, exist_ok=True)
                    import time
                    fname = Path(data.get("filename", "file")).name
                    fpath = folder / f"{int(time.time() * 1000)}_{fname}"
                    fpath.write_bytes(base64.b64decode(data.get("data_base64", "")))
                    ext = fpath.suffix.lower()
                    kind = data.get("kind") or ("image" if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp") else "video" if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm") else "file")
                    self._json({"path": str(fpath), "name": fname, "kind": kind})
                elif path == "/api/files/list":
                    self._json({"items": filetools.list_dir(data.get("path", ""), cfg)})
                elif path == "/api/files/read":
                    self._json(filetools.read_file(data.get("path", ""), cfg))
                elif path == "/api/files/write":
                    self._json(filetools.write_file(data.get("path", ""), data.get("content", ""), cfg, bool(data.get("binary"))))
                elif path == "/api/files/reveal":
                    self._json(filetools.reveal(data.get("path", ""), cfg))
                elif path == "/api/shell":
                    cwd = data.get("cwd") or None
                    if cwd and not filetools.is_allowed(cwd, cfg):
                        self._json({"error": "cwd 不在允许范围内"}, 403)
                        return
                    self._json(shelltools.run(data.get("cmd", ""), cwd, bool(data.get("confirm")), cfg))
                elif path == "/api/screenshot":
                    out_dir = Path(cfg["sessions_dir"]) / "shots"
                    self._json(shot.capture(str(out_dir)))
                elif path == "/api/zip":
                    p = filetools.safe_path(data.get("path", ""), cfg)
                    self._json(archive.zip_path(str(p), cfg["outputs_dir"]))
                elif path == "/api/office":
                    app = data.get("app")
                    p = filetools.safe_path(data.get("path", ""), cfg) if data.get("path") else None
                    if app == "word":
                        if data.get("action") == "create":
                            self._json(office.word_create(str(p), data.get("text", "")))
                        else:
                            self._json(office.word_append(str(p), data.get("text", "")))
                    elif app == "ppt":
                        self._json(office.ppt_create(str(p), data.get("slides", [])))
                    else:
                        self._json({"error": "未知 office 应用"}, 400)
                elif path == "/api/memory":
                    memory.mem_set(data.get("project", ""), data.get("key", ""), data.get("value", ""))
                    self._json({"ok": True})
                elif path == "/api/config":
                    for k in ("allowed_roots", "models_dir", "outputs_dir", "max_history", "default_provider"):
                        if k in data:
                            cfg[k] = data[k]
                    config.save(cfg)
                    self._json({"config": config.public(cfg)})
                else:
                    self._json({"error": "not found"}, 404)
            except BrokenPipeError:
                pass
            except Exception as e:
                try:
                    self._json({"error": str(e)}, 500)
                except Exception:
                    pass

    return Handler


def serve(cfg=None, open_browser=True, host="127.0.0.1"):
    import webbrowser

    cfg = cfg or config.load()
    port = int(cfg.get("port", 8765))
    httpd = ThreadingHTTPServer((host, port), make_handler(cfg))
    url = f"http://127.0.0.1:{port}/"
    print(f"LocalClaw 已启动（仅本机可访问）: {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
