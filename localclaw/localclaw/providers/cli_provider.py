import subprocess
from pathlib import Path

MAX_ARG = 30000


def run(provider, prompt, cwd, args_template, timeout=900):
    exe = provider.get("exe")
    if not exe:
        return {"ok": False, "error": "未找到该模型文件夹中的可执行文件", "output": ""}
    args = [a.replace("{prompt}", prompt) for a in args_template]
    if any(len(a) > MAX_ARG for a in args):
        cwdp = Path(cwd) if cwd else Path.cwd()
        pf = cwdp / ".localclaw_prompt.md"
        pf.write_text(prompt, encoding="utf-8")
        args = [a.replace("{prompt}", "@" + pf.name) if "{prompt}" in a else a for a in args_template]
    cmd = [exe] + args
    try:
        proc = subprocess.run(
            cmd, cwd=cwd or None, capture_output=True, text=True, timeout=timeout
        )
        output = proc.stdout or ""
        if proc.stderr:
            output += ("\n[stderr]\n" + proc.stderr) if output else proc.stderr
        return {"ok": proc.returncode == 0, "output": output, "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"执行超时（{timeout}s）", "output": ""}
    except Exception as e:
        return {"ok": False, "error": str(e), "output": ""}
