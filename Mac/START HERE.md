# Yobot on the Mac

> **¿Prefieres español?** Lee **`EMPIEZA AQUI (Espanol).md`**, en esta misma carpeta.

Yobot is a robot head that listens, thinks and talks back. This guide gets it
running on a Mac.

You need:

- A Mac
- Yobot, its power supply, and its USB cable
- Internet — Yobot's voice and brain live online
- A free **Microsoft Azure** account, for the voice — see Step 3
- An account with **one** AI company, *only* if you want Yobot to hold a
  conversation. Several will do, and Step 3 lists them

---

## What you are setting up

**One installation.** This project is Yobot itself — the motors, the voice, the
moving mouth, and a control panel you drive from a web browser. Everything
below sets that up, and it is the same for everybody.

Two things sit on top of it. Neither changes the install:

- **Chess.** A second project that borrows this one's voice and motors so
  Yobot can play a game out loud against a guest. Add it whenever you like —
  there is a short section near the end of this page. It asks for no account
  of its own.
- **Conversation.** Yobot listening and talking back. The code is already
  here; it needs one AI account to switch on, and Step 3 says how. You can add
  that later without redoing anything.

**Azure is the one account you actually need**, because Azure is the voice.
Without it Yobot still moves — it just does it in silence.

---

## Step 1 — Get the Yobot files

Open Terminal and paste these three lines:

```
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/boquetebots/OhbotPi.git OhbotPi2
```

**No git?** Open <https://github.com/boquetebots/OhbotPi>, use the green
**Code** button and **Download ZIP**, unzip it into `~/Projects`, and rename
the folder from `OhbotPi-main` to `OhbotPi2`.

> **Why that exact place?** The chess project finds this one by looking in the
> folder next door, so `~/Projects/OhbotPi2` sitting beside `~/Projects/Chess`
> means there is nothing to configure. Even if you never add chess, putting it
> there costs nothing and saves moving it later.

---

## Step 2 — One-time Mac setup

**Step 1 — Create Yobot's own Python environment (a "venv").** This is a private sandbox just for Yobot's packages — it avoids the Mac's "externally-managed-environment" complaints entirely. Open Terminal and paste these two lines:

```
python3 -m venv ~/yobot-venv
~/yobot-venv/bin/pip install pyserial lxml httpx flask openai azure-cognitiveservices-speech
```

From now on, always run Yobot with `~/yobot-venv/bin/python3` instead of plain `python3` — that's the whole trick, no "activating" needed. (The commands below are already written that way.)

**Step 2 — Microphone permission.** The first time Yobot listens, macOS will pop up *"Terminal would like to access the microphone"* — click **Allow**. If you accidentally click Don't Allow, fix it in System Settings → Privacy & Security → Microphone → turn on Terminal.

---

## Step 3 — Get your keys

Yobot's voice and its brain are online services, and the files you downloaded
deliberately contain nobody's keys.

**You need the Azure one.** It is the voice.

1. Go to <https://portal.azure.com> and create a free account
2. Search for **Speech** and create a **Speech** resource — the free tier is fine
3. Choose any region (`eastus` will do) and write it down
4. Open **Keys and Endpoint** and copy **KEY 1**

**The brain is optional, and it can wait.** It is what lets Yobot hold a
conversation. Nothing else uses it — not the motors, not the control panel,
not chess. Pick **one** company:

| Company | Where the key comes from | Worth knowing |
|---|---|---|
| **OpenAI** | platform.openai.com → API keys | The default, and what Yobot has always used. |
| **Anthropic** | console.anthropic.com → API keys | Claude. |
| **Google Gemini** | aistudio.google.com/apikey | Has a free tier. |
| **Groq** | console.groq.com → API keys | Runs open models on its own hardware — fast, and very cheap. |
| **Ollama** | nothing to sign up for | Runs on your own Mac or network. No account, no bill. |

**Putting them in.** In `~/Projects/OhbotPi2` there is a file called
`.env.example`. Copy it to `.env` and open it in TextEdit:

```
cd ~/Projects/OhbotPi2
cp .env.example .env
open -e .env
```

Two Azure lines are a complete, working file — with those, Yobot moves, speaks
and plays chess:

```
AZURE_SPEECH_KEY=the key you copied from Azure
AZURE_SPEECH_REGION=eastus
```

Switching the conversation on is two more lines — which company, and its key:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=the key you copied
```

Swap in whichever you chose: `anthropic` with `ANTHROPIC_API_KEY`, `gemini`
with `GEMINI_API_KEY`, `groq` with `GROQ_API_KEY`, or `ollama`, which needs no
key at all. Leave `LLM_PROVIDER` out and Yobot assumes OpenAI, exactly as it
always did.

**Or skip the file entirely** and use the Launcher's Settings page instead —
see below. It is the easier way, and it can test each key for you.

---

## The Web Pages on the Mac

Each page is served by its own program. Start the one you want, then open the address in the Mac's browser. `localhost` just means "this computer" — on the Pi you would use the Pi's own address instead.

| Page | Start it with | Then open |
|------|--------------|-----------|
| **Launcher** (buttons for everything else) | `~/yobot-venv/bin/python3 launcher_server.py` | http://localhost:5000 |
| **Sequence Builder** | `~/yobot-venv/bin/python3 gui_server.py` | http://localhost:5001/gui |
| **Timeline** | (same server as above) | http://localhost:5001/timeline |
| **Calibration** | `~/yobot-venv/bin/python3 calibration_server.py` | http://localhost:5003/calibration |

Run them from the project folder: `cd ~/Projects/OhbotPi2` first. Ctrl-C stops a server.

**The Launcher page is the easy way** — start just that one, and its buttons start and stop the others for you.

**It also has a `⚙ Settings & Keys` link**, which is where the keys from Step 3
really belong. It lets you paste your Azure key, choose which AI company the
brain uses, pick a model, and press a button that checks each one actually
answers — all in the browser, no file editing. Anyone on the same WiFi can open
the Launcher, so the first time you use Settings it offers to set a password;
until you set one it stays unlocked, so a fresh install cannot lock you out of
the page you need to set it from.

Two differences from the Pi version:

- **Shut Down / Restart buttons are hidden** on the Mac (a web page shouldn't be able to switch off your laptop).
- Starting the **conversation bot** opens a **new Terminal window** so you can see it and press Enter to wake it. Close that window or press Ctrl-C in it to stop the bot.

**Port note:** calibration moved from 5002 to **5003**. On the Pi, calibration and the conversation brain server both used 5002 and never noticed, because they never ran at the same time. On the Mac they can, so they now have separate ports. Ports are: 5000 launcher, 5001 GUI/Timeline, 5002 brain server, 5003 calibration.

## The Three Ways to Run It

```
~/yobot-venv/bin/python3 yobot_mac.py test                     ← moves only, no internet needed
~/yobot-venv/bin/python3 yobot_mac.py say "Hello from my Mac"  ← voice + lip sync test
~/yobot-venv/bin/python3 yobot_mac.py                          ← the full conversation bot
```

Do them in that order on the first day — each one tests a little more.

In the full bot: talk to Yobot normally. When it falls asleep, **press Enter** to wake it. **Ctrl-C** quits.

## Adding chess

The chess show is a second project that borrows this one's voice and motors so
Yobot can play a game out loud — against a guest, or against a second robot on
another machine.

Once `yobot_mac.py test` works:

```
cd ~/Projects
git clone https://github.com/boquetebots/YobotChess.git Chess
cd Chess
bash install.sh
```

Then open **`START HERE - Mac.md`** inside it. It asks for no keys of its own —
it uses the Azure voice from Step 3, and it never touches the conversation key.

---

## Troubleshooting

**"Robot not found"** — same old friend, same fix: unplug the USB cable, wait 5 seconds, plug back in, run again. Also check the cable went into the Mac, not the Pi.

**No sound** — check the Mac isn't muted and the right output is chosen in System Settings → Sound. Yobot uses whatever the Mac's default speaker is.

**Bot doesn't hear you** — almost always the microphone permission (see one-time setup above), or the wrong input device selected in System Settings → Sound → Input.

**"AZURE_SPEECH_KEY not found"** — there is no `.env` file where the program is looking. Make sure you are running from the project folder (`cd ~/Projects/OhbotPi2`), that `.env` is in it, and that the name is exactly `.env` — the Finder hides extensions, so a file made in TextEdit can quietly be `.env.txt`. Step 3 covers making it.

**Brain server didn't start** — run it by hand to see the real error: `~/yobot-venv/bin/python3 ohbotchat_server.py`

**"No module named ..." errors** — you probably ran plain `python3` instead of `~/yobot-venv/bin/python3`. The venv's python is the one with all the packages.

---

## What the Mac does not do

- **Auto-start on boot.** That is a Pi thing. On the Mac you start Yobot when
  you want it.

Windows is supported as well — its guide is in the `Windows` folder.

## Background — what got built for the Mac

*Port notes from August 2026, kept for reference. Nothing here is a step.*

| File | What it is |
|------|-----------|
| `yobot_core.py` | **New.** The shared robot library. Detects Pi / Mac / Windows automatically and picks the right audio player, serial port style, and settings. All the motor, LED, eye, and lip-sync code lives here now. |
| `ohbot_pi.py` | Now a 3-line forwarder to yobot_core. Every existing program on the Pi keeps working, unchanged. |
| `yobot_mac.py` | **New.** The Mac launcher — test mode, speech mode, and the full conversation bot. |
| `ohbot_azure.py` | Updated: uses the **default Mac microphone and speaker** automatically. On the Pi, the mic is now a setting (`AZURE_MIC_DEVICE` in .env) instead of buried in code. |
| `ohbot_chat.py` | Updated: on a Mac, **press Enter to wake** a sleeping Yobot (replaces the GPIO button). Chime plays through the cross-platform player. |
| `ohbotchat_server.py` | Updated: loads the API keys from .env itself, so it runs by hand on any machine. |

The Mac and the Pi run the same files. Most people keep a copy on each machine and `git pull` to stay in step; it is also possible to point the Mac at a project folder shared from the Pi over the network, in which case the Pi has to stay switched on for the Mac to read it.

---

## Moving Yobot between a Pi and the Mac

*Only if you have both. Only one computer can hold the robot's cable.*

1. Stop whatever the Pi is running, so it lets go of the cable. If the Pi runs
   Yobot as a service, that is:
   ```
   ssh <your-user>@<your-pi-address> "sudo systemctl stop ohbot-server ohbot-conversation"
   ```
2. Unplug Yobot's **USB cable from the Pi** and plug it into the **Mac**.
3. Run the hardware test (first time, or any time something seems off):
   ```
   cd ~/Projects/OhbotPi2 && ~/yobot-venv/bin/python3 yobot_mac.py test
   ```
   Head moves and eye colours change = success.

## Handing Yobot back to the Pi

1. Quit the bot on the Mac (Ctrl-C).
2. Plug the USB cable back into the Pi.
3. Start its services again:
   ```
   ssh <your-user>@<your-pi-address> "sudo systemctl start ohbot-server ohbot-conversation"
   ```

---

## What Changed on the Pi

Nothing you have to do — but two files were updated and behave slightly differently:

- **`launcher_server.py`** still uses the systemd services on the Pi exactly as before. It checks at startup whether the services are installed and only then uses them; it prints which mode it's in when it starts.
- **`calibration_server.py`** now runs on port **5003** instead of 5002 (the launcher page's calibration link was updated to match). Its "Stop & Exit" button still stops the systemd service on the Pi, and simply exits the program everywhere else.

If the Pi has an `ohbot-calibration` systemd service that hardcodes port 5002 anywhere, it doesn't matter — the port lives in the Python file, not the service.
