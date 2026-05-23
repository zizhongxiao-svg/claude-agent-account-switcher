# Claude Agent Account Switcher

Safe static-context takeover for Claude Code Agent View across multiple local Pro accounts.

This is not a profile manager and not a credential switcher. It does one narrow job: when one Claude Code account hits a session/quota limit, copy the static Agent View continuation context to another local Claude account so you can keep working there.

Claude Code Agent View stores useful continuation context in `projects/` and `jobs/`, but live process state in `sessions/` and daemon files is tied to the account/config that started it. These tools copy only the static context so you can switch accounts after quota limits without sharing credentials, tokens, daemon state, locks, or PID files.

## Why This Exists

Most multi-account tools solve login/profile switching. This project solves a different problem:

> "My Agent View tasks are already blocked by quota. I have another signed-in Claude Code account. Move the task context there without corrupting live session state."

The safe boundary is:

- copy static `projects/` history
- copy static `jobs/` metadata
- never copy live `sessions/`
- never copy credentials
- never symlink multiple accounts to one mutable state directory

## What It Solves

If you use separate Claude Code config dirs such as:

```bash
cca   # ~/.claude
c1a   # ~/.claude-c1
c2a   # ~/.claude-c2
```

you can move static task context like this:

```bash
cca-freeze-import --source-config ~/.claude --target c1 --force
c1a
```

Then continue the imported sessions from the target account.

## Commands

- `cca-freeze-import`: copies static `projects/` and `jobs/` context from one Claude config dir to another. By default, it replaces old freeze-imported context in the target so Agent View does not pile up stale tasks.
- `ccwhere`: shows which account/config appears to have the latest activity.
- `cca-handoff`: exports live Agent View tasks into markdown continuation prompts.

## What It Is Not

- Not an OAuth/token manager.
- Not a Claude Code wrapper.
- Not a daemon or background service.
- Not a live shared state system.
- Not a way to move already-running Claude Code processes between accounts.

If you want account login/profile management, use a profile switcher. If you want to continue static Agent View context after quota limits, use this.

## Install

```bash
git clone https://github.com/zizhongxiao-svg/claude-agent-account-switcher.git
cd claude-agent-account-switcher
./install.sh
```

Add aliases like these to your shell:

```bash
alias cca='claude agents'
alias c1a='CLAUDE_CONFIG_DIR=~/.claude-c1 claude agents'
alias c2a='CLAUDE_CONFIG_DIR=~/.claude-c2 claude agents'

alias cctoc1='cca-freeze-import --source-config ~/.claude --target c1 --force'
alias cctoc2='cca-freeze-import --source-config ~/.claude --target c2 --force'
alias c1toc2='cca-freeze-import --source-config ~/.claude-c1 --target c2 --force'
alias c2toc1='cca-freeze-import --source-config ~/.claude-c2 --target c1 --force'
alias c1tocc='cca-freeze-import --source-config ~/.claude-c1 --target cca --force'
alias c2tocc='cca-freeze-import --source-config ~/.claude-c2 --target cca --force'
```

## Daily Workflow

Find the latest account:

```bash
ccwhere
```

Move from the latest account to the next account:

```bash
cctoc1
c1a
```

or:

```bash
c1toc2
c2a
```

By default, `cca-freeze-import` removes previous freeze-imported context from the target before importing the latest source. This avoids stale tasks piling up in Agent View. It does not remove sessions created natively in the target account unless they were previously created by this tool.

## Comparison

There are good tools in the Claude Code ecosystem for adjacent problems:

- Claude Switch / CCS-style tools: launch Claude Code with separate profile directories.
- Credential switchers: manage OAuth/token switching.
- Full profile managers: manage multiple Claude/Codex profiles and sometimes offer session merge/split.
- Agent dashboards/IDEs: manage multiple agents visually.

This project is smaller and more specific. It assumes you already have multiple local Claude config dirs, for example `~/.claude`, `~/.claude-c1`, and `~/.claude-c2`. It then performs a safe freeze/import of Agent View context between them.

| Need | This project |
| --- | --- |
| Keep multiple accounts logged in | No |
| Switch OAuth credentials | No |
| Launch Claude with a named profile | No |
| Copy blocked Agent View task context to another account | Yes |
| Avoid copying `sessions/`, daemon state, locks, and credentials | Yes |
| Replace old imported tasks instead of piling them up | Yes |

## Safety Model

Copied:

- `projects/**/*.jsonl`
- `jobs/*/state.json`
- `jobs/*/timeline.jsonl`

Never copied:

- credentials
- `sessions/`
- daemon state
- lock files
- shell snapshots
- paste cache

This is a snapshot/takeover tool, not a live shared state system. Do not symlink multiple Claude config dirs to the same `projects/` or `jobs/` directories.

## Limitations

- Claude Code internals may change. The tool is intentionally conservative and only copies files that are useful static context today.
- Imported tasks are context snapshots. Verify the working tree and runtime state before claiming prior work is complete.
- If two accounts keep working on the same copied session independently, their histories diverge. Use `ccwhere` and import from the account that has the latest work.
- The tool does not bypass Claude usage limits. It only helps move local context between accounts you already control.

## Tests

```bash
python3 tests/test_freeze_import.py
python3 tests/test_handoff.py
python3 -m py_compile bin/cca-freeze-import bin/cca-handoff bin/ccwhere
```

## License

MIT
