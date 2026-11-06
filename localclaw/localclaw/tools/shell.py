import re
import subprocess

DANGEROUS = [
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f",
    r"\bdel\s+/[sSqQ]",
    r"\brd\s+/s",
    r"\brmdir\s+/s",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\breg\s+delete\b",
    r"\bdiskpart\b",
    r"\bmkfs",
    r"\bdd\s+if=",
    r"/dev/sd",
    r"\bcipher\s+/w",
    r"Remove-Item[^|;]*-Recurse",
    r"New-Item[^|;]*-ItemType\s+File.*-Force.*del",
]


def is_dangerous(cmd):
    return any(re.search(p, cmd, re.IGNORECASE) for p in DANGEROUS)


def run(cmd, cwd, confirm, cfg, timeout=300):
    if is_dangerous(cmd) and not confirm:
        return {"ok": False, "error": "危险命令，需要用户确认后才能执行（confirm=true）", "dangerous": True}
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd or None, capture_output=True, text=True, timeout=timeout
        )
        output = proc.stdout or ""
        if proc.stderr:
            output += ("\n[stderr]\n" + proc.stderr) if output else proc.stderr
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"命令超时（{timeout}s）"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
