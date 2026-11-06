from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    path: str
    body: str
    dir: str


def parse_skill_md(text):
    meta = {}
    body = text
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for line in lines[1:i]:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")
                body = "\n".join(lines[i + 1:])
                break
    return meta, body


def scan(dirs):
    skills = []
    seen = set()
    for d in dirs:
        p = Path(d).expanduser()
        if not p.is_dir():
            continue
        for child in sorted(p.iterdir()):
            if not child.is_dir():
                continue
            f = child / "SKILL.md"
            if not f.exists():
                continue
            meta, body = parse_skill_md(f.read_text(encoding="utf-8", errors="replace"))
            name = meta.get("name") or child.name
            if name in seen:
                continue
            seen.add(name)
            skills.append(
                Skill(
                    name=name,
                    description=meta.get("description", ""),
                    path=str(f),
                    body=body.strip(),
                    dir=str(child),
                )
            )
    return skills
