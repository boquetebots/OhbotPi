# Setting Up Your Raspberry Pi for the First Time

This is Step 1 for a brand new Ohbot install. If your Pi is already set up and running, skip this guide entirely.

---

## What Is a Raspberry Pi?

A Raspberry Pi is a small, credit-card-sized computer. It runs Linux, an operating system similar to Windows or macOS but free and very lightweight. It doesn't come with an OS installed — you put it on a MicroSD card, which works like the Pi's hard drive.

---

## What You'll Need

### Hardware

| Item | Notes |
|------|-------|
| Raspberry Pi (3B+, 4, or 5) | Pi 4 is the recommended choice — good balance of speed and cost |
| MicroSD card | 32GB minimum, 64GB recommended. Get a reputable brand: Samsung, SanDisk, or Lexar. Cheap cards fail. |
| MicroSD card reader | Most laptops have one built in. If not, a USB adapter costs a few dollars. |
| Power supply | Must match your Pi model — see note below |
| USB-A to USB-B cable | This connects Ohbot to the Pi |
| USB microphone | Only needed for voice input |
| Network connection | Wired ethernet is more reliable, but WiFi works fine |

**Power supply by model:**
- Pi 3 — Micro-USB, 5V/2.5A
- Pi 4 — USB-C, 5V/3A
- Pi 5 — USB-C, 5V/5A (use the official Pi 5 power supply — it's fussy about this)

> **Pi 5 audio note:** The Raspberry Pi 5 does **not** have a headphone jack. Ohbot's speaker needs audio output, so you'll need a small USB audio adapter (a $5–10 USB-to-audio dongle works fine) or a DAC HAT board.

---

## Step 1 — Download Raspberry Pi Imager

Raspberry Pi Imager is a free tool that writes the operating system onto your SD card. It's the official, easiest way to do this.

1. Go to [https://www.raspberrypi.com/software](https://www.raspberrypi.com/software)
2. Download the version for your computer (Windows, Mac, or Linux)
3. Install it like any normal program

---

## Step 2 — Write the OS to Your SD Card

1. Insert your MicroSD card into your computer's card reader

2. Open **Raspberry Pi Imager**

3. Click **Choose Device** and select your Pi model

4. Click **Choose OS**
   - Select **Raspberry Pi OS (64-bit)**
   - This is the standard option — it's what this project was built and tested on

5. Click **Choose Storage** and select your SD card
   - Be careful here — pick the right drive. Everything on it will be erased.

6. Click **Next**

7. A box will pop up asking **"Would you like to apply OS customisation settings?"**
   - Click **Edit Settings** — this is important, don't skip it

---

## Step 3 — Configure Your Pi Before You Boot It

This step lets you set up WiFi, a username, and SSH access *before* you even put the card in the Pi. It saves you from needing a monitor or keyboard attached to the Pi.

In the settings window, fill in the following:

### General tab

| Setting | What to enter |
|---------|--------------|
| **Set hostname** | A name for your Pi on the network, like `ohbot` |
| **Set username and password** | Pick a username (e.g. `pi`) and a strong password. **Write these down.** |
| **Configure wireless LAN** | Enter your WiFi network name (SSID) and password |
| **Wireless LAN country** | Set this to your country |
| **Set locale settings** | Set your timezone and keyboard layout |

> **Username tip:** Whatever username you pick here is what you'll use throughout the rest of the setup guides. When you see `YOUR_USERNAME` in any guide, this is what it means.

### Services tab

- Turn on **Enable SSH**
- Leave it set to **Use password authentication**

Click **Save**, then click **Yes** when asked if you want to apply the settings.

Click **Yes** again to confirm you want to erase the card and write the OS.

Writing the card takes 3–10 minutes depending on your card reader speed. Wait for it to finish completely before removing the card.

---

## Step 4 — First Boot

1. Eject the SD card from your computer safely
2. Insert it into the MicroSD slot on your Pi (the slot is on the underside)
3. Plug in your ethernet cable (if using wired) or skip if using WiFi
4. Plug in the power supply

The Pi will boot. The first boot takes **2–3 minutes** — it's doing initial setup behind the scenes. The green activity light on the Pi will flicker while it works. Wait until it settles down before trying to connect.

---

## Step 5 — Find Your Pi on the Network

You need the Pi's IP address to connect to it.

**Option A — Try the hostname first (easiest)**

If you set the hostname to `ohbot`, try connecting by name:

```bash
ssh YOUR_USERNAME@ohbot.local
```

This works on most home networks without needing to look up the IP address.

**Option B — Find the IP address from your router**

1. Log into your router's admin page (usually at `192.168.1.1` or `192.168.0.1` in a browser)
2. Look for a "Connected Devices" or "DHCP Clients" list
3. Find the device named `ohbot` (or whatever hostname you set)
4. Note the IP address — it will look like `192.168.1.42`

**Option C — Use a network scanner app**

Apps like **Fing** (free, iOS and Android) will scan your network and list all connected devices with their IP addresses.

---

## Step 6 — Connect via SSH

Once you have the IP address or hostname:

**On Mac or Linux:**

Open Terminal and type:

```bash
ssh YOUR_USERNAME@ohbot.local
```

or

```bash
ssh YOUR_USERNAME@192.168.1.42
```

(use whichever works)

The first time you connect, you'll see a message like:

```
The authenticity of host 'ohbot.local' can't be established.
Are you sure you want to continue connecting? (yes/no)?
```

Type `yes` and press Enter. This is normal — it's just your computer remembering the Pi for future connections.

Enter your password when prompted. You won't see anything typed — that's also normal, it's a security feature.

**On Windows:**

Use PuTTY (see the API Keys Setup guide for PuTTY instructions). Enter `ohbot.local` or the IP address as the hostname.

---

## Step 7 — Update the Pi

Once connected, run these two commands to make sure everything is up to date. This can take 5–10 minutes the first time.

```bash
sudo apt update
sudo apt upgrade -y
```

When it finishes, reboot:

```bash
sudo reboot
```

Wait about 30 seconds, then SSH back in.

---

## Your Pi Is Ready

You now have a Raspberry Pi that is:
- ✅ Running the latest Raspberry Pi OS
- ✅ Connected to your network
- ✅ Accessible via SSH from your computer
- ✅ Up to date

**Next step:** Follow the main setup guide (`REBUILD_GUIDE.md`) to install the Ohbot software.

---

## Troubleshooting

**Can't connect — "Connection refused" or "No route to host"**
- The Pi may still be booting. Wait another minute and try again.
- Double-check the IP address or hostname.
- If using WiFi, make sure you entered the correct WiFi password in the Imager settings. If you made a mistake, re-flash the card with the correct settings.

**Pi boots but won't connect to WiFi**
- Check that the wireless LAN country was set correctly in Imager — some countries restrict which WiFi channels are used, and a wrong country setting can prevent connection.
- Try a wired ethernet cable to rule out WiFi as the issue.

**Forgot your password**
- You'll need to re-flash the SD card. There's no easy password reset on a headless Pi. This time, write the password down!

**Green light stays solid or doesn't come on**
- The SD card may not have written correctly. Re-flash it and try again.
- Make sure the card is fully seated in the slot.
