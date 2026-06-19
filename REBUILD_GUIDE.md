# Ohbot Pi — Fresh Rebuild Guide
**Biblioteca de Boquete | Last updated: June 2026**

This guide walks through rebuilding the Ohbot project on a brand-new Raspberry Pi OS installation from scratch. Follow the steps in order.

---

## What You'll Need Before You Start

- The rebuild zip: `Ohbot_rebuild_2026-06-13.zip`
- A MicroSD card (32GB or larger)
- The Raspberry Pi Imager app on your Mac (free from raspberrypi.com)
- Your API keys (they're in the .env file inside the zip, but good to have handy)
- A USB keyboard and HDMI monitor — helpful for the first boot, though not strictly required

---

## Step 1 — Flash a Fresh PiOS

1. Open **Raspberry Pi Imager** on your Mac
2. Click **Choose Device** → select Raspberry Pi 4
3. Click **Choose OS** → select **Raspberry Pi OS (64-bit)** (the full desktop version)
4. Click **Choose Storage** → select your MicroSD card
5. Click **Next**, then click **Edit Settings** when it asks about OS customisation
6. Fill in:
   - **Hostname:** `ohbot` (makes it easier to find on the network)
   - **Username:** `YOUR_USERNAME`
   - **Password:** (set something you'll remember)
   - **WiFi:** your network name and password
   - **Locale/timezone:** Panama / America_Panama
7. Click the **Services** tab and **enable SSH**
8. Click **Save**, then **Yes** to apply, then **Yes** to write
9. Wait for it to finish, then put the MicroSD card in the Pi and power it on

---

## Step 2 — Find the Pi's IP Address

The Pi will connect to your WiFi and get an IP address automatically. You need to find out what that address is.

**Option A — Check your router (easiest)**
Log into your router's admin page (usually `http://192.168.50.1` or similar in a browser). Look for "Connected Devices" or "DHCP Clients" and find a device named `ohbot`.

**Option B — Use your Mac's Terminal**
```bash
ping ohbot.local
```
If the Pi is on the network, this will show its IP address. Press Ctrl-C to stop.

**Option C — Use a network scanner**
Download the free app **LanScan** from the Mac App Store. It lists every device on your network with its IP address.

**Once you have the IP address, write it down.** The old IP was `192.168.50.155` — it may or may not be the same on a fresh install.

---

## Step 3 — Give the Pi a Permanent IP Address

On a fresh install, the Pi's IP address can change every time it reboots. Fix this in your router so it always gets the same address.

Log into your router's admin page, find the DHCP or "Address Reservation" section, and reserve an IP for the Pi by its MAC address. Assign it `192.168.50.155` (the old address) so everything stays the same — or pick any address and note it down.

---

## Step 4 — SSH Into the Pi

On your Mac, open **Terminal** and connect:

```bash
ssh YOUR_USERNAME@192.168.50.155
```

Replace `192.168.50.155` with the actual IP if it's different. Type `yes` if asked about the host key, then enter the password you set in Step 1.

You're now controlling the Pi from your Mac.

---

## Step 5 — Copy the Zip to the Pi

Still in Terminal on your Mac (not SSH — open a new tab with Cmd-T):

```bash
scp ~/Projects/OhbotPi2/Ohbot_rebuild_2026-06-13.zip YOUR_USERNAME@192.168.50.155:~/
```

This copies the zip file to the Pi's home folder. It will take a minute or two.

---

## Step 6 — Unzip and Set Up the Project Folder

Back in your SSH session on the Pi:

```bash
mkdir -p ~/Projects
cd ~/Projects
unzip ~/Ohbot_rebuild_2026-06-13.zip
ls Ohbot/
```

You should see all the project files listed.

---

## Step 7 — Create the Virtual Environment

The zip does not include the virtual environment (venv) — it has to be built fresh on each Pi. This is normal.

```bash
cd ~/Projects/Ohbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The pip install will take several minutes on the Pi, especially the Azure SDK. That's normal — let it run.

When it's done, your terminal prompt should show `(venv)` at the beginning. That means the virtual environment is active.

---

## Step 8 — Check Your API Keys in .env

The `.env` file came with the zip and should already have your keys in it. Verify:

```bash
cat ~/Projects/Ohbot/.env
```

You should see your real Azure and OpenAI keys. If anything looks wrong, edit it:

```bash
nano ~/Projects/Ohbot/.env
```

The file should look like this (with your real keys):
```
OPENAI_API_KEY=sk-...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
```

Save with Ctrl-X, Y, Enter.

---

## Step 9 — Verify the Setup

Run the built-in checker to confirm everything is connected. The verify script needs a couple of extra flags to find your API keys and the Ohbot module correctly:

```bash
cd ~/Projects/Ohbot
source venv/bin/activate
export $(cat .env | xargs)
PYTHONPATH=/home/YOUR_USERNAME/Projects/Ohbot python3 tests/verify_setup.py
```

All seven checks should show green. Fix any red X items before moving on.

> **Note:** If you run `python3 tests/verify_setup.py` without the extra commands above, you'll see false failures for "Azure Credentials" and "Ohbot Module" — this is just a path quirk in the test script and does NOT mean the bot is broken. The bot itself loads `.env` and finds `ohbot_pi.py` automatically.

---

## Step 10 — Install the Autostart Services

This makes the bot start automatically every time the Pi boots, without needing a login:

```bash
cd ~/Projects/Ohbot
bash setup_autostart.sh
```

The script will:
- Create the two systemd services (ohbot-server and ohbot-conversation)
- Enable them to start at boot
- Start them now

If it asks you for a password, use the Pi's login password.

---

## Step 10b — Verify the Microphone Device

The USB microphone must be on card 3 for Azure Speech to work. Confirm it:

```bash
arecord -l
```

You should see something like:
```
card 3: Audio [USB Audio], device 0: USB Audio [USB Audio]
```

If the card number is **3**, you're good — the code is already set up for `plughw:3,0`.

If it's a **different number**, update the code to match:
```bash
sed -i 's/plughw:3,0/plughw:X,0/' ~/Projects/Ohbot/ohbot_azure.py
```
(Replace `X` with the actual card number shown by `arecord -l`.)

---

## Step 11 — Set Up SAMBA (Mac File Sharing)

SAMBA lets the Ohbot folder appear as a shared drive on your Mac, so Claude Cowork can read and edit files directly without SSH.

**Install SAMBA on the Pi:**
```bash
sudo apt update
sudo apt install samba -y
```

**Configure the share:**
```bash
sudo nano /etc/samba/smb.conf
```

Scroll to the very bottom and add:
```
[Projects]
   path = /home/YOUR_USERNAME/Projects
   browseable = yes
   read only = no
   guest ok = no
   create mask = 0664
   directory mask = 0775
```

Save with Ctrl-X, Y, Enter.

**Set a SAMBA password** (separate from your Pi login password):
```bash
sudo smbpasswd -a YOUR_USERNAME
```

**Restart SAMBA:**
```bash
sudo systemctl restart smbd
sudo systemctl enable smbd
```

---

## Step 12 — Connect Your Mac to the Pi's Shared Folder

1. Open **Finder** on your Mac
2. In the menu bar: **Go → Connect to Server** (or press **⌘K**)
3. Type: `smb://192.168.50.155/Projects` (use your actual IP if different)
4. Click **Connect**
5. Enter username `YOUR_USERNAME` and the SAMBA password you just set
6. The Projects folder will appear in Finder

To reconnect automatically every time you log into your Mac: go to **System Settings → General → Login Items** and add the mounted drive.

---

## Step 13 — Reconnect Claude Cowork

1. Open **Claude** on your Mac
2. In Cowork mode, click the folder icon
3. Select the mounted Pi share (it will appear as a drive in the left sidebar of the file picker)
4. Select the `Projects` folder

---

## Step 14 — Update the IP Address in CLAUDE.md

If the Pi's IP address changed from `192.168.50.155`, update it in two places:

**In `~/Projects/OhbotPi2/CLAUDE.md`** — find the line that says `Pi IP address` and update it.

You can also tell Claude in your next session: "The Pi's IP address is now X.X.X.X" and Claude will use that going forward.

---

## Step 15 — Quick Test

Make sure everything is running:

```bash
ssh YOUR_USERNAME@192.168.50.155
systemctl --user status ohbot-server
systemctl --user status ohbot-conversation
```

Both should show `active (running)` in green. If not:

```bash
systemctl --user start ohbot-server
sleep 10
systemctl --user start ohbot-conversation
```

---

## Useful SSH Commands

```bash
# Check if services are running
systemctl --user status ohbot-server
systemctl --user status ohbot-conversation

# Stop everything (required before running the GUI)
systemctl --user stop ohbot-server ohbot-conversation

# Start everything
systemctl --user start ohbot-server

# View live logs
journalctl --user -u ohbot-server -f
journalctl --user -u ohbot-conversation -f

# Restart after code changes
systemctl --user restart ohbot-server ohbot-conversation
```

---

## If Something Goes Wrong

**"WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED" when using SSH or SCP**
Your Mac remembers the old Pi's security fingerprint. Clear it and reconnect:
```bash
ssh-keygen -R 192.168.50.155
```
Then retry your SSH or SCP command and type `yes` when asked to confirm the new fingerprint.

**Can't find the Pi on the network**
Make sure the Pi is powered on and the WiFi credentials were entered correctly in the Imager. Try `ping ohbot.local` from your Mac. If that fails, connect a keyboard and monitor to the Pi to check its status.

**SAMBA connection refused from Mac**
Run `sudo systemctl status smbd` on the Pi to confirm SAMBA is running. Make sure your Mac and Pi are on the same WiFi network.

**Bot starts but robot doesn't move**
Unplug and replug the Ohbot USB cable from the Pi. If it still doesn't respond, stop and restart the services.

**Azure speech errors**
Double-check the `.env` file has your real key and that `AZURE_SPEECH_REGION` matches your Azure subscription region (usually `eastus`).

**Microphone not working / `SPXERR_MIC_NOT_AVAILABLE` error**
The USB microphone is on card 3, but Azure defaults to the system's default audio device (which is different). The fix is a one-line change in `ohbot_azure.py`. Run this on the Pi:
```bash
grep "AudioConfig" ~/Projects/Ohbot/ohbot_azure.py
```
You should see: `audio_config = speechsdk.audio.AudioConfig(device_name="plughw:3,0")`

If it instead says `use_default_microphone=True`, run:
```bash
sed -i 's/use_default_microphone=True/device_name="plughw:3,0"/' ~/Projects/Ohbot/ohbot_azure.py
```

To confirm the mic is on card 3, run `arecord -l` — look for "USB Audio" and note the card number. If it's not card 3, change `3` in `plughw:3,0` to match.

**"Robot not found" / red dot in GUI**
See above — unplug and replug the USB cable, then restart the server.

---

## Reference

| What | Details |
|------|---------|
| Pi IP address | `192.168.50.155` (update if changed) |
| SSH command | `ssh YOUR_USERNAME@192.168.50.155` |
| SAMBA share | `smb://192.168.50.155/Projects` |
| Project folder on Pi | `/home/YOUR_USERNAME/Projects/Ohbot/` |
| GUI URL | `http://192.168.50.155:5001/gui` |
| Bot URL | `http://192.168.50.155:5000` |
| Rebuild zip | `Ohbot_rebuild_2026-06-13.zip` in OhbotPi2 folder |
