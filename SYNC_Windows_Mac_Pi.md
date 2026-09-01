# Keeping Windows, the Mac and the Pi in sync

Written 2026-08-12, when the Windows PC joined the project.

---

## First, the thing you were worried about

You asked how to push *only* the changes each machine needs, so Windows files
don't land on the Pi and Mac files don't land on Windows.

**Git can't do that, and you don't want it to.** Here's why that's fine.

Git has one shared history. Everybody who pulls gets every file. There's no
per-machine filter — that's not a setting someone forgot to add, it's just not
how git works.

But think about what actually happens if `yobot_win.py` lands on the Pi: it sits
there. 13 KB of text. Nothing runs it. The Pi's launcher never calls it. It
costs you nothing.

**The files that would genuinely cause damage are a completely different set** —
and your `.gitignore` already blocks all of them:

| Blocked file | What would happen if it were shared |
|---|---|
| `.env` | Your real API keys on public GitHub |
| `ohbotData/active_robot.txt` | Pi forgets which robot it is after a pull |
| `ohbotData/MD_*.omd` (scratch copies) | Mac's servo calibration overwrites the Pi's — servos stall |
| `logs/` | Every machine's log noise in every diff |
| `__pycache__/` | Compiled Python from the wrong OS |

That's the real hazard list, and it's handled. Platform code files aren't on it.

**So: share everything, let each machine ignore what it doesn't run.** Your
naming already makes it obvious which is which — `yobot_win.py`, `yobot_mac.py`,
`ohbot_pi.py`, `*.bat` for Windows, `*.command` for the Mac, `*.sh` for the Pi.

> One thing I'd advise against: reorganising into `windows/`, `mac/` and `pi/`
> folders. Every `import` line in every Python file would need rewriting, and
> you'd be fixing broken paths for a week. The flat layout with clear names is
> doing the job.

---

## Your daily routine

### On Windows

Double-click **`push-to-github.bat`** in `C:\Projects\OhbotPi2`.

It checks you're on the right branch, checks nobody else pushed first, scans
everything for API keys, asks what you changed, then sends it. If anything
looks wrong it stops and puts things back.

If you'd rather type it, the long way is:

```
cd /d C:\Projects\OhbotPi2
git pull origin main
git add -A
git commit -m "what I changed"
git push origin main
```

### On the Mac

Double-click `push_to_github.command` (as you already do), or:

```bash
cd ~/Projects/OhbotPi2
git pull origin main
```

### On the Pi

```bash
cd ~/Projects/Ohbot
git pull origin main
sudo systemctl restart ohbot-gui
```

That restart line matters. Without it the new files are downloaded but the old
version keeps running until you reboot.

---

## The one rule that prevents 90% of git headaches

**Pull before you start work. Push when you finish.**

Trouble comes from editing the same file on two machines without syncing in
between. Git then has to guess which version wins, and it asks you to sort out
a merge conflict — which is genuinely annoying.

The scripts help: `push-to-github.bat` refuses to run if GitHub has moved ahead
of you, and tells you to pull first.

---

## What I changed today

**1. Added `.gitattributes`** — this one is important and invisible.

Windows ends each line of a text file with two hidden characters. Mac and Linux
use one. When a file crosses between them, git converts — and that conversion
*breaks shell scripts*. You'd have pushed `install.sh` from Windows, pulled it
on the Pi, and got:

```
bash: ./install.sh: /bin/bash^M: bad interpreter: No such file or directory
```

That error is baffling if you haven't seen it before, and there was nothing
stopping it from happening. Now there is. You never have to think about it.

**2. Added `*.backup` to `.gitignore`** — you had three of these
(`ohbot_chat.py.backup`, `ohbot_azure.py.backup`, `knowledge_base.py.backup`)
queued to be pushed. They're snapshots of half-finished work; the Pi doesn't
need them.

**3. Cleared a stuck git lock file.** Your repo had a leftover
`.git/index.lock` from 08:39 this morning — a crashed git process. Any git
command that tried to write would have failed with *"Another git process seems
to be running"*. Removed. (Your `unstick_git.command` on the Mac does the same
job; there's no Windows equivalent yet — if it happens again, just delete
`C:\Projects\OhbotPi2\.git\index.lock`.)

**4. Added `push-to-github.bat`** — the Windows twin of your Mac push script.

---

## Your API keys: checked, and clean

I looked at the working files *and* the entire commit history:

- `.env` (real keys) — ignored, never committed. Correct.
- `git_keys.txt` — ignored. Correct.
- `SSH key regen.txt` — ignored. Correct.
- `.env.example` — committed, but contains only `your_azure_speech_key_here`
  style placeholders. Correct, and useful for anyone setting up fresh.
- `docs/API_KEYS_SETUP.md` — committed, placeholders only. Fine.
- **Nothing key-shaped anywhere in the git history.** Nothing to rotate,
  nothing to clean up.

### One quirk to be aware of

Your `.gitignore` contains these two lines:

```
*key*
*keys*
```

That's a wide net — it hides *any* file with "key" in its name. Right now that's
only your two secrets files, so it's doing exactly what you want. But if you
ever create something like `keyboard_test.py` or `hotkeys.js`, git will silently
ignore it and you'll wonder why it never reaches the Pi.

I left it as-is, because silently-too-safe beats accidentally-leaking. Just
remember it exists. To check what's being hidden at any time:

```
git status --ignored
```

---

## When something goes wrong

**"Another git process seems to be running"**
Delete `C:\Projects\OhbotPi2\.git\index.lock` and try again.

**"Updates were rejected because the remote contains work you do not have"**
Someone pushed from the Mac or Pi first. Run `git pull origin main`, then push.

**`git pull` says it would overwrite your local changes**
You edited a file on that machine. If you don't care about those edits:
`git reset --hard origin/main`. This throws away your edits to code files but
does **not** touch your `.env` or your saved sequences. If you *do* care about
them, stop and ask Claude first.

**Something got pushed that shouldn't have been**
Don't try to fix it with more git commands — that usually makes it worse.
Ask Claude, and say what the file was.
