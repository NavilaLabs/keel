---
description: Enable or disable the keel status line, which shows the active ticket, the current step and whether a consultation is waiting. Use when the user asks to turn the keel status line on or off, or asks how to see keel's status.
---

# Enable the keel status line

A plugin cannot set `statusLine` itself - only `agent` and
`subagentStatusLine` are honoured in a plugin's own settings. So this has to
patch the user's settings once per machine.

`$ARGUMENTS` may be `off` to remove it again. Anything else means enable.

## Enabling

1. Read `~/.claude/settings.json`. If it does not exist, treat it as `{}`.
2. **If a `statusLine` is already configured and it is not keel's**, stop and
   ask before touching it. The user built that, and replacing it silently
   would be a poor trade for a badge. Offer either to replace it or to leave
   it alone, and say what the keel line would show.
3. Set:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "python3 \"<plugin root>/statusline/keel_status.py\""
     }
   }
   ```

   Resolve `<plugin root>` to the real installed path rather than writing the
   variable: `${CLAUDE_PLUGIN_ROOT}` is set for hooks, not for the status
   line command. Look under `~/.claude/plugins/` for the installed `keel`
   directory and use that absolute path.
4. Preserve every other key in the file. Write it back, and tell the user it
   appears from their next message onward - the status line renders per
   conversation turn, not at startup.

## Disabling

Remove the `statusLine` key if its command points at keel. If it points
somewhere else, say so and change nothing.

## What it shows

```
⚓ keel                              installed, this repo not set up
⚓ keel · no ticket                  set up, nothing active
⚓ keel · PROJ-1234 · intake 2       working through intake
⚓ keel · PROJ-1234 · block-1 · 7.2  inside a theme block
⚓ keel · PROJ-1234 · 7 · waiting on you   a consultation is open
```
