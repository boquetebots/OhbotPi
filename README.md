# Yobot — a robot head that listens, thinks and talks back

A talking, moving [Ohbot](https://www.ohbot.co.uk) robot head. It hears you, works
out a reply, and says it out loud with its mouth moving in time with the words.

Runs on a **Raspberry Pi**, a **Mac**, or a **Windows PC** — the same code on all
three. Built by a retired show tech who wanted to control a robot without writing
code every time. 😄

![Status: Working](https://img.shields.io/badge/status-working-brightgreen)

---

## Start here — open the folder for your computer

Everything you need is in one folder. You can ignore the rest.

| If you're on... | Open this folder | And read |
|---|---|---|
| **Windows** | `Windows` | [START HERE.md](Windows/START%20HERE.md) |
| **Mac** | `Mac` | [START HERE.md](Mac/START%20HERE.md) |
| **Raspberry Pi** | `Raspberry Pi` | [START HERE.md](Raspberry%20Pi/START%20HERE.md) |
| **Raspberry Pi, en español** | `Raspberry Pi` | [EMPIEZA AQUI.md](Raspberry%20Pi/EMPIEZA%20AQUI%20%28Espanol%29.md) |

Whichever you pick, you'll also need **[two API keys](Getting%20your%20API%20keys.md)** —
one from Microsoft Azure for the voice and the listening, one from OpenAI for the
conversation. Both have free or very cheap tiers.

Each platform folder holds that platform's guide *and* the files you
double-click. Nothing else in the project needs opening.

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

Everything is driven from web pages in your browser. No coding after setup.

---

## Running it

One page starts everything else:

| Your machine | Do this |
|---|---|
| Windows | double-click `Windows\yobot-launcher.bat` |
| Mac | double-click `Mac/Start Ohbot Launcher.command` |
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
| `.env` | It holds API keys. Publishing keys is how people wake up to a large bill. | Copy `.env.example` to `.env` and paste your own keys in. See [Getting your API keys.md](Getting%20your%20API%20keys.md). |
| `ohbotData/MotorDefinitions*.omd` | Every robot's motors are physically slightly different. Someone else's numbers can make yours strain. | Skip it at first — it runs on safe generic limits and says so at startup. Calibrate later from the Calibration page. |

---

## Project layout

Only the top three folders concern a normal user.

```
READ ME FIRST.txt        which folder is yours
Getting your API keys.md needed on every platform

Windows/                 the guide + everything you double-click
   START HERE.md
   SETUP.bat             set up, once
   yobot-test.bat        does the robot move?
   yobot-launcher.bat    use Yobot — the everyday one
   yobot-stop.bat        unstick things
   yobot.bat             the same, from a terminal
   Reference - Windows in detail.md

Mac/
   START HERE.md
   Start Ohbot Launcher.command

Raspberry Pi/
   START HERE.md
   First time Pi setup.md
   EMPIEZA AQUI (Espanol).md  +  .html

install.sh               Pi: run this from the main folder

── below here is the robot itself; you never need to open it ──

launcher_server.py       the control page                 (5000)
gui_server.py            Sequence Builder + Timeline      (5001)
ohbotchat_server.py      the conversation server          (5002)
calibration_server.py    motor calibration                (5003)
ohbot_chat.py            the microphone / speech / movement loop
yobot_core.py            talks to the robot's board over USB
ohbot_azure.py           speech in and out, and the lip sync
knowledge_base.py        what it knows and how it answers

gui/  launcher/  calibration/    the web pages
sequences/                       saved movement sequences
ohbotData/                       motor calibration files
```

---

## Something not working?

Each START HERE guide ends with a troubleshooting section covering the usual
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
repo but are stripped from the archive — `git clone` gets you everything. The
rules are at the bottom of `.gitattributes`.

---

## License

MIT — do whatever you like with it, just give a nod to the original.

## Credits

Built on the [Ohbot Python library](https://github.com/ohbot/ohbot-python) by the
Ohbot team. Speech by [Microsoft Azure](https://azure.microsoft.com/en-us/products/ai-services/ai-speech).
Conversation by [OpenAI](https://openai.com).
