# Yobot — a robot head that listens, thinks and talks back

A talking, moving [Ohbot](https://www.ohbot.co.uk) robot head. It hears you, works
out a reply, and says it out loud with its mouth moving in time with the words.

Runs on a **Raspberry Pi**, a **Mac**, or a **Windows PC** — the same code on all
three. Built by a retired show tech who wanted to control a robot without writing
code every time. 😄

![Status: Working](https://img.shields.io/badge/status-working-brightgreen)

---

## Start here

Pick your machine. Each guide assumes you know nothing about code.

| If you're on... | Read this |
|---|---|
| **Windows** | **[START_HERE_Windows.md](START_HERE_Windows.md)** — blank laptop to talking robot |
| **Mac** | **[SETUP_MacOS.md](SETUP_MacOS.md)** |
| **Raspberry Pi** | **[INSTALL_GUIDE.md](INSTALL_GUIDE.md)** — from a blank SD card |
| **Raspberry Pi, en español** | **[GUIA_ESTUDIANTES_Pi5.md](GUIA_ESTUDIANTES_Pi5.md)** |

Whichever you pick, you'll also need **[two API keys](docs/API_KEYS_SETUP.md)** —
one from Microsoft Azure for the voice and the listening, one from OpenAI for the
conversation. Both have free or very cheap tiers.

---

## What you need

**Hardware**

- An [Ohbot robot head](https://www.ohbot.co.uk), its power supply and USB cable
- A Raspberry Pi 4 or 5, a Mac, or a Windows PC
- A USB microphone, if you want it to hear you
- A speaker — wired is better than Bluetooth, which lags and puts the lip sync out of step

**Accounts**

- **Microsoft Azure** — text-to-speech and speech recognition (free tier available)
- **OpenAI** — the conversation (pay-as-you-go, pennies for light use)

You can run it without either. The motor controls, the eye colours and the
sequence builder all work offline — only speech and chat need the keys.

---

## What it does

- **Greeter** — the conversation. It listens, replies out loud, and moves as it talks.
- **Sequence Builder** — pose the robot with sliders, record keyframes, play it back.
- **Timeline** — a Pro Tools-style editor for longer routines, with speech timed to movement.
- **Motor Calibration** — set each motor's limits from a web page.
- **Bilingual** — every page and the robot's voice work in English and Spanish.

Everything is driven from web pages in your browser, on the same network. No
coding after setup.

---

## Running it

One page starts everything else:

| Your machine | Do this |
|---|---|
| Windows | double-click `yobot-launcher.bat` |
| Mac | double-click `Start Ohbot Launcher.command` |
| Raspberry Pi | it starts on boot — open `http://<your-pi>:5000` |

That page starts and stops the Greeter, the Sequence Builder, the Timeline and
Calibration.

> **Only one of them can run at a time.** They all share the single USB cable to
> the robot and will fight over it. The Launcher handles the swap for you — just
> press the one you want.

Ports, if you ever need them directly: **5000** launcher, **5001** Sequence
Builder and Timeline, **5002** the conversation server, **5003** calibration.

---

## The two files that are not in this download

On purpose, and there is no way around it:

| What | Why it's missing | What to do |
|---|---|---|
| `.env` | It holds API keys. Publishing keys is how people wake up to a large bill. | Copy `.env.example` to `.env` and paste your own keys in. See [API_KEYS_SETUP.md](docs/API_KEYS_SETUP.md). |
| `ohbotData/MotorDefinitions*.omd` | Every robot's motors are physically slightly different. Someone else's numbers can make yours strain. | Skip it at first — it runs on safe generic limits and says so at startup. Calibrate later from the Calibration page. |

---

## Project layout

```
START_HERE_Windows.md   the beginner guide (Windows)
SETUP_MacOS.md          the beginner guide (Mac)
INSTALL_GUIDE.md        the beginner guide (Raspberry Pi)

SETUP.bat               Windows: one-click setup
yobot-launcher.bat      Windows: start the control page
install.sh              Pi: one-command install, sets up autostart

launcher_server.py      the control page you start everything from  (5000)
gui_server.py           Sequence Builder + Timeline                 (5001)
ohbotchat_server.py     the conversation server                     (5002)
calibration_server.py   motor calibration                           (5003)
ohbot_chat.py           the microphone / speech / movement loop

yobot_core.py           talks to the robot's board over USB
ohbot_azure.py          speech in and out, and the lip sync
knowledge_base.py       what it knows and how it answers
knowledge.json          who it is
venue.py                where it is

gui/  launcher/  calibration/    the web pages
sequences/                       saved movement sequences
ohbotData/                       motor calibration files
```

---

## Something not working?

Each setup guide ends with a troubleshooting section covering the usual
suspects — the robot not being found, no sound, the microphone not being heard,
and the firewall prompt on Windows.

The two that catch nearly everyone:

- **Nothing changed after an update?** Your browser is showing a cached page. Hard-refresh it.
- **It greets you then goes quiet?** It's listening to the wrong microphone.

---

## Contributing

Pull requests welcome — new features, bug fixes, better documentation. If you
build something fun with it, share it in the Issues tab. Always good to see what
people make.

**Note for developers:** the Download ZIP is deliberately trimmed to what you
need to *run* the robot. Test scripts, bench tools and project notes live in the
repo but are stripped from the archive — `git clone` gets you everything.

---

## License

MIT — do whatever you like with it, just give a nod to the original.

## Credits

Built on the [Ohbot Python library](https://github.com/ohbot/ohbot-python) by the
Ohbot team. Speech by [Microsoft Azure](https://azure.microsoft.com/en-us/products/ai-services/ai-speech).
Conversation by [OpenAI](https://openai.com).
