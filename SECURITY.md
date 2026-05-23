# Security

This tool is designed to copy only static Claude Code continuation context.

It should not copy credentials, live process state, daemon state, lock files, shell snapshots, or paste caches. If you find a case where sensitive content is exported, please open an issue with a redacted reproduction.

Before publishing or sharing handoff packs, scan them for secrets:

```bash
rg -n "access_token|refresh_token|api[_-]?key|secret|\\.credentials|\\.git-credentials" .
```
