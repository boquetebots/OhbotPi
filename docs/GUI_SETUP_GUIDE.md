# Ohbot Sequence Builder — GUI Setup Guide

The GUI is a web page that runs on the Pi and lets you control Ohbot from any browser on the same network — your laptop, phone, tablet, whatever. You can move motors with sliders, change the eye colour, make Ohbot speak, and build saved sequences of movements.

---

## Before you start

The GUI uses the same USB cable as the conversation bot. **They cannot run at the same time.** Make sure the conversation bot is stopped before launching the GUI.

If you set up autostart with systemd, stop it like this:

```
sudo systemctl stop ohbot-conversation
```

If it's running in a terminal window, just press **Ctrl-C** to stop it.

---

## Step 1 — Open two terminal windows on the Pi

You need two terminals. If you're using tmux (recommended), press `Ctrl-B` then `"` to split the window. If you're SSH'd in from your laptop, just open a second terminal and SSH in again.

---

## Step 2 — Start the GUI server

In one terminal, go to your Ohbot folder and run:

```
python3 gui_server.py
```

You'll see something like this:

```
🎛️   Ohbot Sequence Builder — GUI Server
⚠️  IMPORTANT: Make sure the conversation bot is NOT running.
🔊 Initializing Azure speech...
✅ Azure speech ready
🔌 Connecting to Ohbot hardware...
✅ Ohbot connected on /dev/ttyACM0
✅ Motors reset to neutral

🌐 Open the GUI in your browser:
   http://localhost:5001/gui        (from the Pi)
   http://192.168.1.42:5001/gui    (from your laptop / Mac)
```

Note the IP address it shows — that's the address you'll open in your browser.

---

## Step 3 — Open the GUI in your browser

On your laptop (or any device on the same Wi-Fi), open a browser and go to:

```
http://<the-ip-address-from-above>:5001/gui
```

For example: `http://192.168.1.42:5001/gui`

The page should load and show the control panel. If it doesn't load, double-check that your laptop is on the same Wi-Fi network as the Pi.

---

## What you can do in the GUI

### Motor sliders
Each of Ohbot's 8 motors has its own slider — Head Nod, Head Turn, Eye Turn, and so on. Drag a slider and Ohbot moves in real time.

### Eye colour
Three sliders (R, G, B) control the LED eye colour. Values run from 0 (off) to 10 (full brightness).

### Make Ohbot speak
Type anything into the speech box and click **Speak**. Ohbot will say it out loud with lip sync, using your Azure voice. This is a good way to test new phrases before recording them as WAV files.

### Reset
The Reset button sends all motors back to their neutral (centre) positions and turns off the LEDs.

### Sequence Builder
You can build a timeline of keyframes — snapshots of motor positions and LED colours at specific moments in time. 

- Set up a pose with the sliders, then click **Add Keyframe** to save that pose at the current time.
- Add as many keyframes as you like to build a full movement sequence.
- Click **Play** to watch Ohbot perform the sequence on the robot.
- Click **Save** to give it a name and store it to disk.
- Saved sequences appear in the list on the left — click any one to load it back.

Sequences are saved as `.json` files inside a `sequences/` folder next to the Python scripts.

---

## Stopping the GUI

Press **Ctrl-C** in the terminal where `gui_server.py` is running.

When you're done in the GUI and want to run the conversation bot again:

```
sudo systemctl start ohbot-conversation
```

Or just run it manually in a terminal:

```
python3 ohbot_server.py
```
(in one terminal) and
```
python3 ohbot_conversation.py
```
(in the other).

---

## Troubleshooting

**The page loads but sliders don't move Ohbot**  
Ohbot isn't being found on the USB serial cable. Check the cable is plugged in and that the conversation bot is fully stopped. Restarting `gui_server.py` usually fixes it.

**"Azure speech not available" when I try to Speak**  
Your `.env` file is missing or the Azure keys aren't filled in. Check that `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` are set in your `.env` file.

**Can't reach the page from my laptop**  
Make sure your laptop and the Pi are on the same Wi-Fi network. Some networks block devices from talking to each other (guest networks often do this). Try using the Pi's hotspot if you have one set up.

**Port 5001 already in use**  
Another copy of `gui_server.py` is already running. Find it with `ps aux | grep gui_server` and kill it with `kill <pid>`.
