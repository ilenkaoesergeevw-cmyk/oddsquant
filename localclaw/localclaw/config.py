import json
import os
import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_HOME = Path(os.environ.get("LOCALCLAW_HOME", Path.home() / ".localclaw"))
APP_HOME.mkdir(parents=True, exist_ok=True)

DEFAULT_PORT = 8765


def _default_config():
    return {
        "port": DEFAULT_PORT,
        "token": secrets.token_hex(16),
        "db_path": str(APP_HOME / "memory.db"),
        "models_dir": str(PROJECT_ROOT / "models"),
        "skills_dirs": [
            str(PROJECT_ROOT / "skills"),
            str(APP_HOME / "skills"),
            str(Path.home() / ".openclaw" / "skills"),
        ],
        "allowed_roots": [str(Path.home())],
        "outputs_dir": str(APP_HOME / "outputs"),
        "sessions_dir": str(APP_HOME / "sessions"),
        "max_history": 30,
        "disabled_skills": [],
        "default_provider": "",
        "provider_args": {
            "claude": ["-p", "{prompt}", "--output-format", "json"],
            "codex": ["exec", "{prompt}"],
            "qwen": ["-p", "{prompt}"],
            "custom": ["{prompt}"],
        },
    }


def load():
    cfg_path = APP_HOME / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        base = _default_config()
        base.update(cfg)
        return base
    cfg = _default_config()
    save(cfg)
    return cfg


def save(cfg):
    (APP_HOME / "config.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def public(cfg):
    keys = [
        "port",
        "models_dir",
        "skills_dirs",
        "allowed_roots",
        "outputs_dir",
        "sessions_dir",
        "max_history",
        "disabled_skills",
        "default_provider",
    ]
    return {k: cfg.get(k) for k in keys}
