#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "cca-freeze-import"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(cmd, env=None):
    return subprocess.run(
        cmd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_import_copies_history_and_jobs_but_not_sessions():
    root = Path(tempfile.mkdtemp(prefix="cca-freeze-import-test-"))
    try:
        source = root / "source"
        target = root / "target"
        out = root / "out"
        fake_claude = root / "bin" / "claude"
        fake_claude.parent.mkdir(parents=True)
        fake_claude.write_text(
            "#!/usr/bin/env bash\n"
            "cat <<'JSON'\n"
            "[{\"pid\":222,\"cwd\":\"%s/work\",\"kind\":\"background\","
            "\"sessionId\":\"22222222-2222-4222-8222-222222222222\","
            "\"name\":\"blocked task\",\"status\":\"waiting\"}]\n"
            "JSON\n" % str(root),
            encoding="utf-8",
        )
        fake_claude.chmod(0o755)

        rel_project = Path("projects") / "-tmp-work" / "22222222-2222-4222-8222-222222222222.jsonl"
        write(source / rel_project, '{"type":"user","message":{"content":"continue me"}}\n')
        write(source / "jobs" / "22222222" / "state.json", '{"state":"blocked","intent":"do work"}\n')
        write(source / "sessions" / "222.json", '{"pid":222,"sessionId":"22222222-2222-4222-8222-222222222222"}\n')

        env = os.environ.copy()
        env["PATH"] = str(fake_claude.parent) + os.pathsep + env["PATH"]
        result = run(
            [
                str(SCRIPT),
                "--source-config",
                str(source),
                "--target-config",
                str(target),
                "--output-dir",
                str(out),
            ],
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert (target / rel_project).exists()
        assert (target / "jobs" / "22222222" / "state.json").exists()
        assert not (target / "sessions" / "222.json").exists()
        launch = (out / "resume-target.sh").read_text(encoding="utf-8")
        assert "CLAUDE_CONFIG_DIR=" in launch
        assert "--resume '22222222-2222-4222-8222-222222222222' --fork-session" in launch
    finally:
        shutil.rmtree(root)


def test_import_includes_static_jobs_not_visible_as_live_agents():
    root = Path(tempfile.mkdtemp(prefix="cca-freeze-import-static-test-"))
    try:
        source = root / "source"
        target = root / "target"
        out = root / "out"
        fake_claude = root / "bin" / "claude"
        fake_claude.parent.mkdir(parents=True)
        fake_claude.write_text("#!/usr/bin/env bash\nprintf '[]\\n'\n", encoding="utf-8")
        fake_claude.chmod(0o755)

        sid = "33333333-3333-4333-8333-333333333333"
        rel_project = Path("projects") / "-tmp-static-work" / f"{sid}.jsonl"
        write(source / rel_project, '{"type":"user","message":{"content":"static import only"}}\n')
        write(
            source / "jobs" / "33333333" / "state.json",
            json.dumps(
                {
                    "state": "blocked",
                    "intent": "static imported task",
                    "name": "static task",
                    "sessionId": sid,
                    "resumeSessionId": sid,
                    "cwd": str(root / "static-work"),
                }
            ),
        )

        env = os.environ.copy()
        env["PATH"] = str(fake_claude.parent) + os.pathsep + env["PATH"]
        result = run(
            [
                str(SCRIPT),
                "--source-config",
                str(source),
                "--target-config",
                str(target),
                "--output-dir",
                str(out),
            ],
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert (target / rel_project).exists()
        assert (target / "jobs" / "33333333" / "state.json").exists()
        index = (out / "INDEX.md").read_text(encoding="utf-8")
        assert "static task" in index
    finally:
        shutil.rmtree(root)


def test_replace_source_removes_previous_import_and_overwrites_existing_session():
    root = Path(tempfile.mkdtemp(prefix="cca-freeze-import-replace-test-"))
    try:
        source = root / "source"
        target = root / "target"
        out1 = root / "out1"
        out2 = root / "out2"
        fake_claude = root / "bin" / "claude"
        fake_claude.parent.mkdir(parents=True)
        fake_claude.write_text("#!/usr/bin/env bash\nprintf '[]\\n'\n", encoding="utf-8")
        fake_claude.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(fake_claude.parent) + os.pathsep + env["PATH"]

        sid_old = "44444444-4444-4444-8444-444444444444"
        sid_new = "55555555-5555-4555-8555-555555555555"
        rel_old = Path("projects") / "-tmp-old" / f"{sid_old}.jsonl"
        rel_new = Path("projects") / "-tmp-new" / f"{sid_new}.jsonl"

        write(source / rel_old, "old-v1\n")
        write(
            source / "jobs" / "44444444" / "state.json",
            json.dumps({"name": "old task", "sessionId": sid_old, "cwd": str(root / "old")}),
        )
        first = run(
            [
                str(SCRIPT),
                "--source-config",
                str(source),
                "--target-config",
                str(target),
                "--output-dir",
                str(out1),
                "--replace-source",
                "--force",
            ],
            env=env,
        )
        assert first.returncode == 0, first.stderr
        assert (target / rel_old).read_text(encoding="utf-8") == "old-v1\n"

        shutil.rmtree(source / "projects")
        shutil.rmtree(source / "jobs")
        write(source / rel_new, "new-v1\n")
        write(
            source / "jobs" / "55555555" / "state.json",
            json.dumps({"name": "new task", "sessionId": sid_new, "cwd": str(root / "new")}),
        )
        write(source / rel_old, "old-v2\n")
        write(
            source / "jobs" / "44444444" / "state.json",
            json.dumps({"name": "old task", "sessionId": sid_old, "cwd": str(root / "old")}),
        )
        second = run(
            [
                str(SCRIPT),
                "--source-config",
                str(source),
                "--target-config",
                str(target),
                "--output-dir",
                str(out2),
                "--replace-source",
                "--force",
            ],
            env=env,
        )
        assert second.returncode == 0, second.stderr
        assert (target / rel_old).read_text(encoding="utf-8") == "old-v2\n"
        assert (target / rel_new).exists()
    finally:
        shutil.rmtree(root)


def test_default_import_removes_previous_imports_from_other_sources():
    root = Path(tempfile.mkdtemp(prefix="cca-freeze-import-target-test-"))
    try:
        source_a = root / "source-a"
        source_b = root / "source-b"
        target = root / "target"
        out1 = root / "out1"
        out2 = root / "out2"
        fake_claude = root / "bin" / "claude"
        fake_claude.parent.mkdir(parents=True)
        fake_claude.write_text("#!/usr/bin/env bash\nprintf '[]\\n'\n", encoding="utf-8")
        fake_claude.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(fake_claude.parent) + os.pathsep + env["PATH"]

        sid_a = "66666666-6666-4666-8666-666666666666"
        sid_b = "77777777-7777-4777-8777-777777777777"
        rel_a = Path("projects") / "-tmp-a" / f"{sid_a}.jsonl"
        rel_b = Path("projects") / "-tmp-b" / f"{sid_b}.jsonl"
        write(source_a / rel_a, "from-a\n")
        write(source_a / "jobs" / "66666666" / "state.json", json.dumps({"sessionId": sid_a, "cwd": str(root / "a")}))
        write(source_b / rel_b, "from-b\n")
        write(source_b / "jobs" / "77777777" / "state.json", json.dumps({"sessionId": sid_b, "cwd": str(root / "b")}))

        first = run(
            [
                str(SCRIPT),
                "--source-config",
                str(source_a),
                "--target-config",
                str(target),
                "--output-dir",
                str(out1),
                "--force",
            ],
            env=env,
        )
        assert first.returncode == 0, first.stderr
        assert (target / rel_a).exists()

        second = run(
            [
                str(SCRIPT),
                "--source-config",
                str(source_b),
                "--target-config",
                str(target),
                "--output-dir",
                str(out2),
                "--force",
            ],
            env=env,
        )
        assert second.returncode == 0, second.stderr
        assert not (target / rel_a).exists()
        assert not (target / "jobs" / "66666666" / "state.json").exists()
        assert (target / rel_b).exists()
        assert (target / "jobs" / "77777777" / "state.json").exists()
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    test_import_copies_history_and_jobs_but_not_sessions()
    test_import_includes_static_jobs_not_visible_as_live_agents()
    test_replace_source_removes_previous_import_and_overwrites_existing_session()
    test_default_import_removes_previous_imports_from_other_sources()
    print("ok")
