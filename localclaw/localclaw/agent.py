from . import config, memory
from .providers import scan as scan_providers
from .providers import cli_provider
from .skills import loader as skills_loader

SYSTEM = """你是 LocalClaw，一个运行在本机电脑上的本地智能体，帮助用户写代码、调试程序、操作本机文件。
规则：
1. 你只能访问用户允许的目录（allowed_roots），不要尝试访问范围之外的路径。
2. 删除、覆盖、格式化等危险操作必须先向用户说明后果并征得同意。
3. 涉及秘钥、密码、.env 等敏感文件时不要输出其内容。
4. 回复中引用本机文件时，写出完整路径，方便用户打开查看。
5. 写完文件后提醒用户可以打包为 zip。"""


def build_prompt(cfg, session, user_msg, attachments, skills):
    proj = session.get("project") or ""
    parts = [SYSTEM]
    if proj:
        parts.append(f"当前项目目录: {proj}")
        mem = memory.mem_all(proj)
        if mem:
            lines = "\n".join(f"- {k}: {v}" for k, v in mem.items())
            parts.append(f"该项目的记忆（以前总结的经验，请遵守）:\n{lines}")
    if skills:
        blob = "\n\n".join(f"## 技能: {s.name}\n{s.body}" for s in skills)
        parts.append(f"以下是已启用的技能说明（与 OpenClaw 的 SKILL.md 格式兼容），请按其中方法执行:\n{blob}")
    limit = int(cfg.get("max_history", 30))
    hist = memory.messages(session["id"], limit=limit)
    for m in hist:
        if m["role"] in ("user", "assistant"):
            who = "用户" if m["role"] == "user" else "助手"
            parts.append(f"{who}: {m['content']}")
    parts.append("用户: " + user_msg)
    if attachments:
        parts.append("本次消息附件（本机路径，可直接读取/查看）:")
        for a in attachments:
            parts.append(f"- [{a.get('kind', 'file')}] {a.get('path')} ({a.get('name', '')})")
    return "\n\n".join(parts)


def chat(cfg, session_id=None, title="新任务", project="", message="", provider_id=None, attachments=None, skill_names=None):
    if session_id is None:
        session_id = memory.new_session(title=(title or message[:30] or "新任务"), project=project)
    session = memory.get_session(session_id)
    if not session:
        return {"error": "会话不存在"}
    if project and not session.get("project"):
        memory.set_project(session_id, project)
    memory.add_message(session_id, "user", message, attachments or [])

    providers = scan_providers(cfg["models_dir"])
    ready = [p for p in providers if p.get("ready")]
    prov = None
    if provider_id:
        prov = next((p for p in providers if p["id"] == provider_id), None)
    if prov is None and ready:
        pref = cfg.get("default_provider")
        prov = next((p for p in ready if p["id"] == pref), None) or ready[0]
    if prov is None or not prov.get("ready"):
        reply = "未找到可用模型。请把模型/工具文件夹（如 claude-code、codex、qwen-code）放入软件目录下的 models/ 文件夹，然后点击界面上的“刷新模型”。"
        memory.add_message(session_id, "assistant", reply, [])
        return {"session_id": session_id, "reply": reply, "provider": None, "ok": False}

    disabled = set(cfg.get("disabled_skills", []))
    skills = [s for s in skills_loader.scan(cfg["skills_dirs"]) if s.name not in disabled]
    if skill_names:
        skills = [s for s in skills if s.name in skill_names]

    prompt = build_prompt(cfg, session, message, attachments or [], skills)
    args = cfg.get("provider_args", {}).get(prov["type"], ["-p", "{prompt}"])
    res = cli_provider.run(prov, prompt, project or None, args)
    reply = res.get("output") or res.get("error") or ""
    memory.add_message(session_id, "assistant", reply, [])
    return {"session_id": session_id, "reply": reply, "provider": prov["id"], "ok": res.get("ok", False)}
