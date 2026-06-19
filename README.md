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

## Full Documentation

If this is a brand new install, read the guides in this order:

| Guide | What it covers |
|-------|---------------|
| [Setting Up Your Pi](docs/PI_FIRST_SETUP.md) | SD card, OS install, first boot, SSH access — start here if your Pi is brand new |
| [Getting Your API Keys](docs/API_KEYS_SETUP.md) | Step-by-step for Azure Speech and OpenAI — includes warnings about Azure's confusing interface |
| [Full Rebuild Guide](REBUILD_GUIDE.md) | Complete software install: Python, dependencies, project files, and systemd services |
| [Launcher Setup](LAUNCHER_SETUP.md) | Set up the web launcher so Ohbot starts automatically on boot |
| [Autostart Troubleshooting](docs/AUTOSTART_TROUBLESHOOT.md) | If services won't start on boot, check here |

---

## Quick Setup

> **Brand new Pi?** Start with the [Pi First Setup guide](docs/PI_FIRST_SETUP.md) before continuing here.

### 1. Clone this repo onto your Pi

```bash
cd ~/Projects
git clone https://github.com/YOUR_USERNAME/ohbot-web-gui.git
cd ohbot-web-gui
```

### 2. Install Python dependencies

```bash
pip3 install flask openai azure-cognitiveservices-speech
```

### 3. Create your `.env` file

Copy the example and fill in your keys:

```bash
cp .env.example .env
nano .env
```

The `.env` file should look like this:

```
AZURE_SPEECH_KEY=your_azure_key_here
AZURE_SPEECH_REGION=your_azure_region_here
OPENAI_API_KEY=your_openai_key_here
```

> **Don't have keys yet?** See the [API Keys Setup guide](docs/API_KEYS_SETUP.md) for step-by-step instructions on getting Azure and OpenAI keys.
>
> **Important:** Never share your `.env` file. It contains your private API keys.

### 4. Customize the personality prompts *(optional but recommended)*

Open `gui_server.py` and find the `_PERSONALITIES` section near the top. The default prompts describe Ohbot as a robot at "the Boquete Public Library in Panama" — that's where the original was built. Change these to suit your location and use case.

### 5. Run the server

```bash
python3 gui_server.py
```

Then open a browser on any computer on your local network and go to:

```
http://<your-pi-ip-address>:5001/gui
```

To find your Pi's IP address, run `hostname -I` on the Pi.

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
