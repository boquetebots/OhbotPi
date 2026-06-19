# Ohbot Installation Guide
### From a blank SD card to a talking robot

This guide walks you through everything from setting up a brand-new Raspberry Pi to running Ohbot for the first time. No coding experience required.

---

## What You'll Need Before You Start

- Raspberry Pi 4 (any RAM size)
- A microSD card (16GB or larger)
- A Mac or Windows computer
- The Ohbot USB cable plugged into the Pi
- Your WiFi network name and password
- Your API keys (see below)

### API Keys — Get These First before installing this software 

Ohbot needs two AI accounts before the installer can finish:

**OpenAI** (for the AI brain)
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an account or log in
3. Go to **API Keys** → **Create new secret key**
4. Copy it and save it somewhere safe — you only see it once

**Microsoft Azure** (for voice — speaking and listening)
1. Go to [portal.azure.com](https://portal.azure.com) and create a free account
2. Search for **Speech** and create a new **Speech** resource
3. Choose any region (e.g. `eastus`) — write it down
4. Go to **Keys and Endpoint** — copy **Key 1**

You'll paste both of these in during the install. If you skip them, Ohbot's motor controls and sequences still work — just not the voice or AI features.

---

## Part 1 — Image the SD Card

If you have not setup a Raspberry Pi before, the instructions can be found in REBUILD_GUIDE.md
---

## Part 2 — Boot the Pi and Find Its Address

Every device on your WiFi network has a unique address — like a house number. You need this to connect to the Pi.

1. Put the SD card into the Pi
2. Plug in power — there's no power button, it starts automatically
3. Wait about 60–90 seconds for it to fully boot

### Finding the IP Address

**Easiest way — use the hostname:**
If you set the hostname to `ohbot` during imaging, you can often just use `ohbot.local` instead of a number and the Pi will be found on your local network. Try this first.

**If that doesn't work — check your router:**
1. Open a browser and go to your router's admin page. This is usually `192.168.1.1` or `192.168.0.1` — it's often printed on the bottom of your router.
2. Log in and look for a section called **Connected Devices**, **DHCP Clients**, or **Device List**
3. Find your Pi by the hostname you gave it (e.g. `ohbot`)
4. The number next to it (like `192.168.50.155`) is its IP address — write it down

---

## Part 3 — Connect to the Pi via SSH

SSH stands for Secure Shell. You turned it on when you set up the SD card for the Pi.

> SSH lets you type commands on your Pi from your Mac or Windows computer — without needing a keyboard, screen, or mouse plugged into the Pi.

You open a terminal on your computer, type one command, and suddenly you're working "inside" the Pi. Whatever you type runs on the Pi, not your computer. When you're done, you type `exit` and you're back to your own computer.

That's it. It's a remote control for the command line.

### Open a Terminal

**On a Mac:**
- Press `Command + Space`, type `Terminal`, press Enter

**On Windows:**
- Press the Windows key, type `Terminal` or `PowerShell`, press Enter
- If neither works, download [PuTTY](https://www.putty.org) — it's a free SSH app

---

## Part 4 — SSH Into the Pi

In your terminal, type this command or copy and paste it- then press Enter:

```
ssh username@ohbot.local
```

Replace `username` with the username you chose, and `ohbot.local` with your Pi's hostname or IP address. For example:

```
ssh username@192.168.xxx.xxx
Or
ssh username@ohbot.local
```

**First time only:** It will ask you to confirm a security key fingerprint. Type `yes` and press Enter. You'll only see this once.

Then it will ask for your password. Type the password you set during imaging — you won't see any characters appear as you type, that's normal. Press Enter.

If it works, you'll see something like:

```
username@ohbot:~ $
```

That means you're in. You're now controlling the Pi from your computer.

---

## Part 5 — Download the Ohbot Files

Now that you're inside the Pi, you'll download the Ohbot project files from GitHub. GitHub is a website where code is stored — think of it like Google Drive but for software projects.

First, make sure Git (the tool that downloads from GitHub) is installed.
Type or copy/paste this at the SSH line in terminal:

```
sudo apt install git -y
```

It may already be installed — if so, this will just say so and finish quickly.

Next, create the folder where Ohbot will live:

```
mkdir -p ~/Projects/Ohbot
```

Move into that folder:

```
cd ~/Projects/Ohbot
```

Now download the Ohbot files:

```
git clone https://github.com/boquetebots/OhbotPi.git .
```

> Replace the URL with the actual GitHub address for this project. The dot at the end is important — it puts the files directly in the current folder.

You'll see a list of files downloading. When it finishes, you're ready for the final step.

---

## Part 6 — Run the Installer

This is the easy part. One command, then follow the prompts.
Type or copy/paste this command at the command prompt in terminal:

```
bash install.sh
```

The installer will walk you through each step and tell you what it's doing. When it asks for your API keys, paste in the OpenAI and Azure keys you copied earlier.

At the end, it will ask if you want to start Ohbot right now. Say yes, and within about 30 seconds Ohbot should come to life.

---

## After the Install

Ohbot is now set up to **start automatically every time the Pi powers on**. You don't need to SSH in again for normal use — just plug in the power and wait about 60 seconds.

### Useful Commands (for when you do SSH in)

Watch what Ohbot is doing in real time:
```
journalctl --user -u ohbot-server -f
```
```
journalctl --user -u ohbot-conversation -f
```
Press `Ctrl-C` to stop watching the log.

Stop Ohbot:
```
systemctl --user stop ohbot-server ohbot-conversation
```

Start Ohbot:
```
systemctl --user start ohbot-server
```

### Open the Launcher

On any computer connected to the same WiFi, open a browser and go to:
```
http://ohbot.local:5001
```
Or use the IP address:
```
http://192.168.xxx.xxx:5001
```

This opens the launcher page where you can choose which Ohbot personality to run.

---

## Troubleshooting

**"Robot not found" / red status dot in the GUI**
The USB cable connection got stuck. Unplug and replug the Ohbot USB cable from the Pi, then restart:
```
systemctl --user restart ohbot-server ohbot-conversation
```

**SSH connection refused**
SSH isn't enabled on the Pi. You'll need to re-image the SD card and make sure you turn on SSH in the settings during the Imager step.

**Can't find the Pi on the network**
Make sure you entered the correct WiFi name and password during imaging. Passwords are case-sensitive. If it still won't connect, re-image the card.

**AI responses not working**
Check that your OpenAI key is correct. You can edit it by running:
```
nano ~/Projects/Ohbot/.env
```
Make your changes, press `Ctrl-X`, then `Y`, then Enter to save.
