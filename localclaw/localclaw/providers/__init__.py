import shutil
from pathlib import Path

KNOWN = {
    "claude": {
        "label": "Claude Code",
        "exe": ["claude", "claude.cmd", "claude.exe", "claude.bat"],
    },
    "codex": {
        "label": "ChatGPT Codex",
        "exe": ["codex", "codex.exe", "codex.cmd"],
    },
    "qwen": {
        "label": "Qwen Code",
        "exe": ["qwen", "qwen.cmd", "qwen.exe", "qwen.bat"],
    },
}

EXEC_SUFFIXES = {".exe", ".cmd", ".bat", ".sh", ".ps1"}


def _find_exe(folder: Path, names):
    candidates = [
        folder,
        folder / "bin",
        folder / "node_modules" / ".bin",
        folder / "scripts",
    ]
    for base in candidates:
        if base.is_dir():
            for n in names:
                f = base / n
                if f.is_file():
                    return str(f)
    for n in names:
        w = shutil.which(n)
        if w:
            return w
    return None


def scan(models_dir):
    out = []
    md = Path(models_dir).expanduser()
    if not md.is_dir():
        return out
    for child in sorted(md.iterdir()):
        if not child.is_dir():
            continue
        low = child.name.lower()
        key = None
        for k in KNOWN:
            if k in low:
                key = k
                break
        if key is not None:
            exe = _find_exe(child, KNOWN[key]["exe"])
            out.append(
                {
                    "id": child.name,
                    "type": key,
                    "label": f"{KNOWN[key]['label']} ({child.name})",
                    "exe": exe,
                    "folder": str(child),
                    "ready": exe is not None,
                }
            )
        else:
            exe = None
            for f in sorted(child.iterdir()):
                if f.is_file() and f.suffix.lower() in EXEC_SUFFIXES and not f.name.lower().startswith("readme"):
                    exe = str(f)
                    break
            out.append(
                {
                    "id": child.name,
                    "type": "custom",
                    "label": child.name,
                    "exe": exe,
                    "folder": str(child),
                    "ready": exe is not None,
                }
            )
    return out
