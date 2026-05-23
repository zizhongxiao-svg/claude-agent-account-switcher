#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin" / "cca-handoff"


def run(cmd, **kwargs):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_exports_live_agents_from_mock_config():
    root = Path(tempfile.mkdtemp(prefix="cca-handoff-test-"))
    try:
        config = root / "claude"
        out = root / "out"
        fake_claude = root / "bin" / "claude"
        fake_claude.parent.mkdir(parents=True)
        fake_claude.write_text(
            "#!/usr/bin/env bash\n"
            "cat <<'JSON'\n"
            "[{\"pid\":123,\"cwd\":\"%s/work\",\"kind\":\"background\",\"startedAt\":1,"
            "\"sessionId\":\"11111111-1111-4111-8111-111111111111\","
            "\"name\":\"demo task\",\"status\":\"idle\"}]\n"
            "JSON\n" % str(root),
            encoding="utf-8",
        )
        fake_claude.chmod(0o755)

        session_dir = config / "projects" / "-tmp-work"
        write(
            session_dir / "11111111-1111-4111-8111-111111111111.jsonl",
            json.dumps(
                {
                    "type": "user",
                    "message": {"role": "user", "content": "fix the demo bug"},
                    "timestamp": "2026-05-22T00:00:00Z",
                    "cwd": str(root / "work"),
                    "sessionId": "11111111-1111-4111-8111-111111111111",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": "I changed app.py; access_token=abc123; see .credentials.json",
                    },
                    "timestamp": "2026-05-22T00:01:00Z",
                    "cwd": str(root / "work"),
                    "sessionId": "11111111-1111-4111-8111-111111111111",
                }
            )
            + "\n",
        )
        write(
            config / "jobs" / "11111111" / "state.json",
            json.dumps(
                {
                    "state": "blocked",
                    "needs": "rate limited",
                    "intent": "original request",
                    "cwd": str(root / "work"),
                    "sessionId": "11111111-1111-4111-8111-111111111111",
                },
                indent=2,
            ),
        )
        write(config / ".credentials.json", '{"secret":"must-not-export"}\n')

        env = os.environ.copy()
        env["PATH"] = str(fake_claude.parent) + os.pathsep + env["PATH"]
        result = run(
            [
                str(SCRIPT),
                "--config-dir",
                str(config),
                "--output-dir",
                str(out),
                "--no-git",
                "--tail-lines",
                "20",
            ],
            env=env,
        )
        assert result.returncode == 0, result.stderr
        index = (out / "INDEX.md").read_text(encoding="utf-8")
        assert "demo task" in index
        prompt = (out / "11111111-demo-task.md").read_text(encoding="utf-8")
        assert "fix the demo bug" in prompt
        assert "I changed app.py" in prompt
        assert "rate limited" in prompt
        assert "abc123" not in prompt
        assert "access_token" not in prompt
        assert "must-not-export" not in prompt
        assert ".credentials" not in prompt
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    test_exports_live_agents_from_mock_config()
    print("ok")
