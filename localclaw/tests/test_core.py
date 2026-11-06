import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["LOCALCLAW_HOME"] = tempfile.mkdtemp(prefix="lc-test-")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localclaw import config, memory  # noqa: E402
from localclaw.providers import scan as scan_providers  # noqa: E402
from localclaw.skills import loader as skills_loader  # noqa: E402
from localclaw.tools import archive, files as filetools  # noqa: E402
from localclaw.tools import shell as shelltools  # noqa: E402
from localclaw import agent  # noqa: E402


class TestConfig(unittest.TestCase):
    def test_token_stable(self):
        c1 = config.load()
        c2 = config.load()
        self.assertEqual(c1["token"], c2["token"])
        self.assertTrue(c1["token"])


class TestMemory(unittest.TestCase):
    def test_sessions_and_messages(self):
        sid = memory.new_session("任务A", "/tmp/proj")
        memory.add_message(sid, "user", "你好", [{"path": "/tmp/a.png", "kind": "image"}])
        memory.add_message(sid, "assistant", "你好！")
        msgs = memory.messages(sid)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[0]["attachments"][0]["kind"], "image")
        memory.mem_set("/tmp/proj", "风格", "用中文回复")
        self.assertEqual(memory.mem_get("/tmp/proj", "风格"), "用中文回复")
        self.assertEqual(memory.mem_all("/tmp/proj"), {"风格": "用中文回复"})
        memory.delete_session(sid)
        self.assertEqual(memory.messages(sid), [])
        self.assertIsNone(memory.get_session(sid))


class TestSkills(unittest.TestCase):
    def test_parse_and_scan(self):
        d = Path(os.environ["LOCALCLAW_HOME"]) / "skills" / "my-skill"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            '---\nname: my-skill\ndescription: 测试技能\n---\n\n# 正文\n步骤一。\n', encoding="utf-8"
        )
        skills = skills_loader.scan([str(Path(os.environ["LOCALCLAW_HOME"]) / "skills")])
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "my-skill")
        self.assertIn("步骤一", skills[0].body)


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.cfg = config.load()
        self.root = Path(tempfile.mkdtemp(prefix="lc-root-"))
        self.cfg["allowed_roots"] = [str(self.root)]

    def test_safe_path(self):
        inside = self.root / "a" / "b.txt"
        filetools.write_file(str(inside), "hello", self.cfg)
        r = filetools.read_file(str(inside), self.cfg)
        self.assertEqual(r["text"], "hello")
        with self.assertRaises(PermissionError):
            filetools.safe_path("/etc/passwd", self.cfg)

    def test_list_dir(self):
        (self.root / "sub").mkdir()
        items = filetools.list_dir(str(self.root), self.cfg)
        names = [i["name"] for i in items]
        self.assertIn("sub", names)


class TestShell(unittest.TestCase):
    def test_dangerous(self):
        self.assertTrue(shelltools.is_dangerous("rm -rf /"))
        self.assertTrue(shelltools.is_dangerous("del /s /q C:\\x"))
        self.assertFalse(shelltools.is_dangerous("ls -la"))
        self.assertFalse(shelltools.is_dangerous("echo hello"))


class TestArchive(unittest.TestCase):
    def test_zip(self):
        d = Path(tempfile.mkdtemp(prefix="lc-zip-")) / "proj"
        d.mkdir()
        (d / "main.py").write_text("print(1)", encoding="utf-8")
        out = Path(tempfile.mkdtemp(prefix="lc-out-"))
        r = archive.zip_path(str(d), str(out))
        self.assertTrue(r["zip"].endswith(".zip"))
        self.assertTrue(Path(r["zip"]).exists())
        import zipfile

        with zipfile.ZipFile(r["zip"]) as z:
            self.assertIn("proj/main.py", z.namelist())


class TestProviders(unittest.TestCase):
    def test_scan(self):
        md = Path(tempfile.mkdtemp(prefix="lc-models-"))
        fake = md / "claude-code-local"
        (fake / "bin").mkdir(parents=True)
        exe = fake / "bin" / "claude"
        exe.write_text("#!/bin/sh\necho FAKE-REPLY: $@\n", encoding="utf-8")
        exe.chmod(0o755)
        provs = scan_providers(str(md))
        self.assertEqual(len(provs), 1)
        self.assertEqual(provs[0]["type"], "claude")
        self.assertTrue(provs[0]["ready"])
        self.assertEqual(provs[0]["exe"], str(exe))


@unittest.skipIf(os.name == "nt", "需要 POSIX shell 的伪模型")
class TestAgentChat(unittest.TestCase):
    def test_chat_with_fake_provider(self):
        cfg = config.load()
        md = Path(tempfile.mkdtemp(prefix="lc-models2-"))
        fake = md / "claude-test"
        fake.mkdir()
        exe = fake / "claude"
        exe.write_text("#!/bin/sh\necho \"FAKE-REPLY received\"\n", encoding="utf-8")
        exe.chmod(0o755)
        cfg["models_dir"] = str(md)
        cfg["provider_args"] = {"claude": ["-p", "{prompt}"]}
        proj = tempfile.mkdtemp(prefix="lc-proj-")
        res = agent.chat(cfg, message="你好", project=proj)
        self.assertTrue(res["ok"])
        self.assertIn("FAKE-REPLY", res["reply"])
        msgs = memory.messages(res["session_id"])
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant"])
        memory.mem_set(proj, "备注", "测试项目")
        self.assertEqual(memory.mem_all(proj)["备注"], "测试项目")


if __name__ == "__main__":
    unittest.main()
