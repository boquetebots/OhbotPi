# Ohbot Launcher — Setup Guide

This sets up the launcher so it starts automatically when the Pi boots.

---

## What Changes

| Before | After |
|--------|-------|
| Greeter bot starts on boot automatically | Launcher starts on boot instead |
| No choice | User picks Greeter or GUI from a web page |
| GUI had to be started manually | GUI can be started from the launcher |

---

## Step 1 — Copy the new files to the Pi

Via SAMBA (if mounted) or SCP from your Mac:

```bash
scp launcher_server.py YOUR_USERNAME@192.168.50.155:/home/YOUR_USERNAME/Projects/Ohbot/
scp -r launcher/ YOUR_USERNAME@192.168.50.155:/home/YOUR_USERNAME/Projects/Ohbot/
```

---

## Step 2 — Stop the greeter from auto-starting

SSH into the Pi first:

```bash
ssh YOUR_USERNAME@192.168.50.155
```

Then disable the greeter services so they no longer start on boot:

```bash
systemctl --user disable ohbot-server
systemctl --user disable ohbot-conversation
systemctl --user stop ohbot-server
systemctl --user stop ohbot-conversation
```

---

## Step 3 — Create the launcher user service

The launcher runs as a user service (same type as the greeter).

```bash
nano ~/.config/systemd/user/ohbot-launcher.service
```

Paste this in exactly:

```ini
[Unit]
Description=Ohbot Launcher
After=network.target

[Service]
WorkingDirectory=/home/YOUR_USERNAME/Projects/Ohbot
ExecStart=/home/YOUR_USERNAME/Projects/Ohbot/venv/bin/python3 /home/YOUR_USERNAME/Projects/Ohbot/launcher_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Save and exit (Ctrl-O, Enter, Ctrl-X).

---

## Step 4 — Create the GUI user service

```bash
nano ~/.config/systemd/user/ohbot-gui.service
```

Paste this in:

```ini
[Unit]
Description=Ohbot Sequence Builder GUI
After=network.target

[Service]
WorkingDirectory=/home/YOUR_USERNAME/Projects/Ohbot
ExecStart=/home/YOUR_USERNAME/Projects/Ohbot/venv/bin/python3 /home/YOUR_USERNAME/Projects/Ohbot/gui_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Save and exit.

---

## Step 5 — Allow passwordless shutdown/restart

The launcher's Shut Down and Restart buttons need permission to power off the Pi.
Run this once:

```bash
echo "YOUR_USERNAME ALL=(ALL) NOPASSWD: /sbin/shutdown, /sbin/reboot" | sudo tee /etc/sudoers.d/ohbot-power
```

---

## Step 6 — Enable and start the launcher

```bash
systemctl --user daemon-reload
systemctl --user enable ohbot-launcher
systemctl --user start ohbot-launcher
```

---

## Step 7 — Make sure user services survive reboot without login

This one command tells the Pi to keep your user services running even when nobody is logged in:

```bash
loginctl enable-linger YOUR_USERNAME
```

You only need to run this once.

---

## Step 8 — Test it

Open a browser and go to:

```
http://192.168.50.155:5000
```

You should see the launcher page with two choices.

---

## Checking if it worked

```bash
systemctl --user status ohbot-launcher
```

If something went wrong, check the logs:

```bash
journalctl --user -u ohbot-launcher -n 50
```

---

## Reverting (if you want the old behavior back)

```bash
systemctl --user disable ohbot-launcher
systemctl --user stop ohbot-launcher
systemctl --user enable ohbot-server
systemctl --user enable ohbot-conversation
```
