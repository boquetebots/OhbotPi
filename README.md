# Ohbot Web GUI — Sequence Builder & Controller

A browser-based control panel for the [Ohbot](https://ohbot.readthedocs.io) robot head, running on a Raspberry Pi 4.

Built by a retired show tech who wanted to control a robot without writing code every time. 😄

![Status: Working](https://img.shields.io/badge/status-working-brightgreen)

---

## What It Does

This GUI lets you control and program an Ohbot robot head from any web browser on your local network — no coding required after setup.

**Features:**
- **Live motor sliders** — move all 8 motors in real time (head, eyes, lips, etc.)
- **LED eye colour picker** — full RGB control
- **Emotion presets** — one-click poses: happy, sad, surprised, thinking, sleeping
- **Sequence builder** — create, save, and play back timed animation sequences (keyframes)
- **Text-to-speech** — type something and Ohbot says it out loud with lip sync (requires Azure)
- **Microphone input** — talk to Ohbot using your Pi's USB mic (requires Azure)
- **AI chat panel** — have a conversation with Ohbot powered by GPT (requires OpenAI)
- **Personality switcher** — friendly, comedian, pirate, professor, or shy
- **Demo mode** — a built-in self-running demo that shows off all the moves

---

## What You Need

### Hardware
- [Ohbot robot](https://www.ohbot.co.uk) (the hardware kit)
- Raspberry Pi 4 (any RAM size works)
- USB mic (optional — needed for voice input)

### Accounts & API Keys
- **Microsoft Azure** account — for text-to-speech and speech recognition (free tier available)
- **OpenAI** account — for the AI chat feature (pay-as-you-go, very cheap for light use)

> You can run the GUI without Azure or OpenAI — the motor controls, LED picker, and sequence builder all work without them. Speech and chat just won't be available.

---

## Installation

> **[→ Read the full installation guide](INSTALL_GUIDE.md)**

The install guide covers everything from a blank SD card to a running robot — including what SSH is, how to find your Pi on the network, and how to get your API keys.

The short version, once your Pi is set up and you're SSH'd in:

```bash
cd ~/Projects/Ohbot
git clone https://github.com/boquetebots/OhbotPi.git .
bash install.sh
```

The installer will prompt you for your API keys and handle everything else automatically. Ohbot will be configured to start on every boot.

Then open a browser on any computer on the same WiFi and go to:

```
http://ohbot.local:5001
```

---

## Documentation

| Guide | What it covers |
|-------|---------------|
| [Installation Guide](INSTALL_GUIDE.md) | Complete setup from scratch — Pi imaging, SSH, GitHub clone, running the installer |
| [Rebuild Guide](REBUILD_GUIDE.md) | Full manual setup reference if you prefer to do things step by step |
| [Launcher Setup](LAUNCHER_SETUP.md) | How the web launcher works and how to add new Ohbot personalities |

---

## Important: Two Servers Can't Run at Once

If you're also running the Ohbot conversation bot (a separate project), **stop it before starting this GUI**. Both use the same USB serial cable and they will conflict.

```bash
sudo systemctl stop ohbot-server
sudo systemctl stop ohbot-conversation
```

Restart them when you're done with the GUI.

---

## Project Structure

```
ohbot-web-gui/
├── gui_server.py       # The Flask web server — all the robot control logic
├── ohbot_pi.py         # Low-level Ohbot hardware wrapper
├── ohbot_azure.py      # Azure speech (text-to-speech + microphone input)
├── gui/
│   └── index.html      # The entire browser GUI (one self-contained file)
├── sequences/          # Saved animation sequences (JSON files, created at runtime)
├── .env.example        # Template for your API keys
├── .gitignore          # Keeps your .env out of git
└── README.md
```

---

## How the Sequence Builder Works

1. Use the sliders to pose Ohbot however you like
2. Click **Add Keyframe** to record that pose at the current time
3. Scrub the timeline and add more keyframes
4. Press **Play** to watch Ohbot animate through your sequence
5. Save it with a name — it gets stored as a JSON file in the `sequences/` folder

Sequences can include motor positions, LED colours, and spoken text — all timed together.

---

## Contributing

Pull requests are welcome! If you improve something — new features, bug fixes, better documentation — feel free to open a PR.

If you build something cool with this, share it in the Issues tab. Always fun to see what people make.

---

## License

MIT License — do whatever you want with it, just give a nod to the original.

---

## Credits

Built on top of the [Ohbot Python library](https://github.com/ohbot/ohbot-python) by the Ohbot team.
Speech powered by [Microsoft Azure Cognitive Services](https://azure.microsoft.com/en-us/products/cognitive-services/).
AI chat powered by [OpenAI](https://openai.com).
