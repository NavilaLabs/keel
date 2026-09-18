# keel

> The keel is the first part of a ship to be laid down, and every frame after
> it is measured from it. Get it wrong and nothing built on top of it sits
> straight.

A Claude Code plugin for developing one ticket at a time, with the
architecture decided before the code and the contracts frozen before the
implementation.

Claude writes the code. You decide the boundaries — and keel makes that
decision hold: the LikeC4 model and the stub signatures are agreed at a
consultation, and hooks refuse to let an implementation quietly change them
afterwards.

## Install

```
/plugin marketplace add <path-or-git-url-of-this-repo>
/plugin install keel@keel-marketplace
```

If the install summary says `Run /reload-plugins to activate.`, run it.

For local development on the plugin itself:

```
claude --plugin-dir /path/to/keel
claude plugin validate /path/to/keel
```

## How you can tell it is on

**At session start.** In a repo that is set up for keel, a `SessionStart` hook
tells Claude that keel governs this repository, which ticket is active and
where it stopped. That is what lets `/keel:ticket` resume at step 7 instead of
asking you where things stood. In a repo that is *not* set up, the hook stays
silent — an unconfigured repo is one keel has no opinion about.

**In the status line**, once you turn it on:

```
/keel:statusline
```

```
⚓ keel                                    installed, this repo not set up
⚓ keel · no ticket                        set up, nothing active
⚓ keel · PROJ-1234 · intake 2             working through intake
⚓ keel · PROJ-1234 · block-1 · 7.2        inside a theme block
⚓ keel · PROJ-1234 · 7 · waiting on you   a consultation is open
```

The last line is the one that earns its place. Consultations are where the
workflow hands control back to you, and a run that is waiting looks exactly
like a run that is thinking unless something says so.

This needs a command because a plugin cannot set `statusLine` itself — only
`agent` and `subagentStatusLine` are honoured in a plugin's own settings, so
`/keel:statusline` patches `~/.claude/settings.json` once per machine. If you
already have a status line, it asks before replacing it. `/keel:statusline off`
removes it again.

## Set up a project

Two things per code repo.

**1. Point keel at the ticket repo.** Create `.claude/keel.json` in the code
repo:

```json
{
  "ticket_repo": "../ticket-repo-myproject"
}
```

(`KEEL_TICKET_REPO` in the environment works too and takes precedence.)

**2. Tell it which ticket is active.** The hooks run outside the conversation
and cannot see what you are working on, so the id goes in `.keel-ticket` in
the code repo root — add that to `.gitignore`. `/keel:ticket` writes it for
you. `KEEL_TICKET_ID` in the environment also works.

Without either, the hooks fail open: they warn once and let Claude continue.
That is deliberate — a hook that halts development when it is itself
misconfigured gets disabled within two days, and then it protects nothing.

## Set up the ticket repo

One per project, separate from the code. It holds everything that is not code,
so the code repo stays code:

```
ticket-repo-myproject/
  architecture/          # LikeC4. main = as-is, ticket branch = to-be
    specification.c4
    container-*.c4
    views.c4
  tickets/PROJ-1234/
    knowledge.md         # goals, problems, open questions, jump log
    state.json           # machine-readable workflow state
    events.jsonl         # appended by the state-writer hook
    adr/0001-*.md
```

`example/state.example.json` shows a filled-in state file; `state.schema.json`
is the schema it conforms to. `example/keel.json` is the project config.

## MCP servers

Tickets, pull requests and the architecture model are all reached through MCP,
so `/keel:ticket` can read a Jira issue and update a `.c4` file without you
copying anything between windows:

```bash
claude mcp add atlassian --transport http https://mcp.atlassian.com/v1/sse   # Jira + Bitbucket
claude mcp add github -- npx -y @modelcontextprotocol/server-github          # Issues + PRs
claude mcp add likec4 -- npx -y @likec4/mcp                                  # the model
```

Check each server's own documentation for the current command — these change.

To see the diagrams while you work, run `npx likec4 start` in the ticket repo
for a live-reloading preview, or use the LikeC4 VS Code extension.

## Use

```
/keel:ticket PROJ-1234              # start, or resume exactly where it stopped
/keel:sync-architecture PROJ-1234   # after the PR is merged
/keel:statusline                    # turn the status line on (or: off)
```

`/keel:ticket` reads `state.json` and re-enters at the recorded step. It does
not restart at step 1, and it does not re-run finished steps to refresh
context.

## The workflow

| Zone | Steps | |
| --- | --- | --- |
| Intake | 1 Gather context | via `context-gatherer` |
| | 2 Understand goals and problems | consultation |
| | 3 Ask functional questions | no consultation |
| | 4 Split into theme blocks | consultation |
| | 5 Persist knowledge | consultation |
| Blocks | 6 Collect solution options | via `research-agent`, consultation |
| | 7 Fix architecture and contracts | consultation — the critical one |
| | 8 Implement | no consultation |
| | 9 Verify | no consultation |
| Delivery | 10 Open the PR | |
| | 11 Process PR feedback | via `review-triage` |
| | 12 Sync the as-is model | manual only |

Theme blocks run in parallel through 6 and 7, one at a time from 8 onward.
There is nothing to wait for once consultations stop, and two agents writing
into one branch only produce conflicts.

Step 7 is where the work actually happens: the LikeC4 model gets updated on
the to-be branch, and the contracts get written as empty stubs — trait,
interface, abstract class, whatever the language calls it — with the
guarantees in the doc comments. Everything after 7 is implemented against
those.

### Jumping back

A jump reactivates the target step's own consultation rule, whichever zone it
came from. "No consultation from 8 onward" governs the forward path only.

| From | To | When |
| --- | --- | --- |
| 6/7 | 2 | The goal was misunderstood |
| 7 | 4 | Blocks turned out not to be independent |
| 8 | 7 | A contract has to change |
| 9 | 8 | A plain bug |
| 9 | 7 | A design flaw |
| PR | 1/2/7/8 | Per `review-triage`'s classification |

The threshold: a signature, a guarantee or a model relationship changes →
real jump. A name or a comment changes → just fix it.

## What is in here

**Commands** — `/keel:ticket` orchestrates; `/keel:sync-architecture` is step
12; `/keel:statusline` toggles the status line.

**Subagents** — `context-gatherer` (1), `research-agent` (6.3),
`review-triage` (11.1), `as-is-extractor` (12.1). Each keeps bulk material out
of the main conversation and returns a condensed result. Deliberately none for
step 7 or for consultations: those belong where you can see them.

**Skills** — `artifact-formats`, `likec4-conventions`, `stub-conventions`,
`decision-heuristics`, `consultation-protocol`. Loaded when relevant.

**Hooks** — everything above is convention an agent can drift from. These hold
regardless:

| Hook | Enforces |
| --- | --- |
| `stub_lock` | Contracts frozen at 7.2 cannot change during 8/9 |
| `consultation_gate` | Nothing gets written while a consultation is open |
| `sequential_implementation` | One block at a time in 8/9 |
| `as_is_staleness` | Step 7.0 when main moved under the branch |
| `pr_gate` | No PR before blocks are done and artifacts are linked |
| `block_overlap` | Overlapping component claims mean a jump back to 4 |
| `state_writer` | Appends the event stream to `events.jsonl` |
| `session_start` | Announces keel and the active ticket to Claude |

`stub_lock` is the one that matters. It locks the *file* declaring a contract
rather than parsing signatures, which is what makes it work across Rust, PHP
and Dart without a parser per language. Keep contracts in their own files;
where the language will not allow it, mark the stub `"shared_file": true` and
the hook warns instead of blocking.

The hooks need Python 3. Nothing else.

## Toward a UI

Everything a UI would need is already recorded, so it can be built later
without touching the workflow: `state.json` for the current position,
`events.jsonl` for the live stream and history, `consultations[]` as
addressable objects renderable as cards, `artifacts.c4_views` for which
diagram to show, `jump_log[]` for why things changed.

## License

MIT.
