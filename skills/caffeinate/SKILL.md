---
name: caffeinate
description: Keep the Mac awake using macOS `caffeinate`, like the Amphetamine app. It works as a chat front end: show presets, the user says what they need in plain words, and Claude runs it. Use when the user says /caffeinate or asks to keep the Mac, screen or system awake: for a duration, until a set time, while an app, process or command runs, or with the lid closed. Also use to check what is keeping the Mac awake, or to stop keep-awake sessions.
---

# Caffeinate: Claude Edition

Act as a client for `caffeinate`, like Amphetamine on macOS. Show the menu,
let the user reply in plain words, then run the command. Don't ask
follow-up questions when a sensible default exists.

## On invocation

1. Check the current state:
   ```bash
   pgrep -lf '^caffeinate' || echo "none running"
   pmset -g assertions | grep -E '^\s+(PreventUserIdleSystemSleep|PreventUserIdleDisplaySleep|PreventSystemSleep) '
   cat "$TMPDIR/claude-caffeinate.pids" 2>/dev/null
   ```
2. Show a one-line status. If sessions are running, list their PID, flags
   and time left. Say which ones Claude started, meaning PIDs listed in the
   pid file.
3. Show the menu below. If the user already said what they want when
   invoking, skip the menu and run it.

## Menu

| # | Preset | What stays awake | Command |
|---|---|---|---|
| 1 | **Indefinitely** | Screen and system | `caffeinate -dimsu` |
| 2 | **Indefinitely, screen can sleep** | System only | `caffeinate -ims` |
| 3 | **For a duration** (30m / 1h / 2h / 4h / custom) | Screen and system | `caffeinate -dimsu -t <sec>` |
| 4 | **Until a set time** ("until 18:30") | Screen and system | `-t` with the seconds worked out |
| 5 | **While an app/process runs** ("while Zoom is open") | Screen and system | `caffeinate -dimsu -w <pid>` |
| 6 | **While a command runs** ("while `npm run build` runs") | System | `caffeinate -i <cmd>` |
| 7 | **Closed-lid / server mode** (AC power) | System | `caffeinate -s` |
| 8 | **Nudge**: register one bit of user activity | Resets the idle timer | `caffeinate -u -t 1` |

Flags you can combine: `-d` display, `-i` idle system sleep, `-m` disk,
`-s` system (AC only), `-u` user activity, `-t N` seconds, `-w PID`.

Controls: **status**, **stop** (sessions Claude started), **stop all**
(every caffeinate process).

## Reading requests

- "Screen can sleep" or "system only": drop `-d` and `-u`.
- If the user doesn't mention the screen, keep both screen and system
  awake (`-dimsu`).
- Durations: turn `30m`, `1.5h`, `90 min` and similar into seconds.
- "Until HH:MM" or "until 6pm": target epoch minus now. If that time has
  already passed today, use tomorrow:
  ```bash
  t=$(date -j -f "%H:%M:%S" "18:30:00" +%s); now=$(date +%s)
  [ "$t" -le "$now" ] && t=$((t + 86400)); echo $((t - now))
  ```
- "While <app> runs": find the PID with `pgrep -x '<Name>'`, falling back
  to `pgrep -if '<name>'`. Pick the main process, not the helpers. Zoom's
  process is `zoom.us`. If nothing matches, say so. If several processes
  match and none is clearly the main one, ask which.
- "While <command> runs": run `caffeinate -i <command>` in the foreground
  or with `run_in_background`, depending on how long it takes. Don't
  detach it, because the user wants to see its output.

## Starting a session

Detach it so it outlives this Claude session, then record the PID:

```bash
nohup caffeinate -dimsu -t 7200 >/dev/null 2>&1 &
pid=$!; disown; echo "$pid" >> "$TMPDIR/claude-caffeinate.pids"; echo "$pid"
```

Afterwards, confirm in one line what stays awake and until when, giving
the local clock time for timed sessions. Example: "☕ Screen and system
awake until 16:42 (PID 12345)."

## Status

Run the checks from "On invocation". For sessions with `-t`, work out the
time left from the start time (`ps -o lstart= -p <pid>`). Also list any
other processes holding sleep assertions (`pmset -g assertions`), such as
video players or backups, so the user knows what else is keeping the Mac
awake.

## Stopping

- **stop**: kill the live PIDs from the pid file, then remove the file:
  ```bash
  f="$TMPDIR/claude-caffeinate.pids"
  [ -f "$f" ] && while read -r p; do kill "$p" 2>/dev/null; done < "$f"; rm -f "$f"
  ```
- **stop all**: `pkill -x caffeinate`. This also kills sessions started
  by other tools, so list them and confirm first, unless the user already
  said "all".
- **stop <pid>**: kill just that PID.

Before starting a new session, remove dead PIDs from the pid file.

## Caveats (mention only when relevant)

- `-s` only works on AC power.
- On a MacBook, closing the lid can still put it to sleep unless it's on
  AC power, an external display is connected, or
  `sudo pmset -a disablesleep 1` is set. Offer that last option, and don't
  run it without explicit consent, because it needs sudo and changes the
  setting system-wide until it's undone.
- `$TMPDIR` resets on reboot. After a restart, the old caffeinate
  processes are gone anyway.
