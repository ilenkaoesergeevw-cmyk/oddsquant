import base64
import os
import subprocess
import sys
from pathlib import Path


def allowed_roots(cfg):
    return [Path(r).expanduser().resolve() for r in cfg.get("allowed_roots", [])]


def is_allowed(path, cfg):
    try:
        rp = Path(path).expanduser().resolve()
    except Exception:
        return False
    return any(rp == r or r in rp.parents for r in allowed_roots(cfg))


def safe_path(path, cfg):
    if not is_allowed(path, cfg):
        raise PermissionError(f"路径不在允许范围内: {path}")
    return Path(path).expanduser().resolve()


def list_dir(path, cfg):
    p = safe_path(path, cfg)
    if not p.is_dir():
        raise NotADirectoryError(str(p))
    items = []
    for f in sorted(p.iterdir()):
        try:
            items.append(
                {
                    "name": f.name,
                    "path": str(f),
                    "is_dir": f.is_dir(),
                    "size": f.stat().st_size if f.is_file() else 0,
                }
            )
        except OSError:
            continue
    return items


def read_file(path, cfg, max_bytes=200000):
    p = safe_path(path, cfg)
    data = p.read_bytes()
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    try:
        return {"path": str(p), "text": data.decode("utf-8"), "truncated": truncated, "binary": False}
    except UnicodeDecodeError:
        return {
            "path": str(p),
            "text": base64.b64encode(data).decode(),
            "truncated": truncated,
            "binary": True,
        }


def write_file(path, content, cfg, binary=False):
    p = safe_path(path, cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(content) if binary else content.encode("utf-8")
    p.write_bytes(data)
    return {"path": str(p), "size": len(data)}


def reveal(path, cfg):
    p = safe_path(path, cfg)
    if os.name == "nt":
        subprocess.Popen(["explorer", "/select," + str(p)] if p.is_file() else ["explorer", str(p)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p.parent)])
    return {"revealed": str(p)}
