# Yobot — Fresh Build Checklist

Building a new Raspberry Pi from scratch to run Yobot at the Rincón Clubhouse.

| | |
|---|---|
| **Hostname** | `yobot1` |
| **Username** | `yobot` |
| **Project folder on the Pi** | `/home/yobot/Projects/Ohbot/` |
| **Repo** | `https://github.com/boquetebots/OhbotPi.git` |
| **Old Pi (for reference)** | user `<your-user>`, IP `<your-pi-address>` |

**Do not reformat the old SD card.** It is your only way back if this goes
wrong. Put it in a drawer until Yobot has worked at the Clubhouse for a week.

---

## The one thing to do before anything else

You could not find the Pi on the library network yesterday. That will happen
again. Read **[Part 9 — Finding the Pi](#part-9--finding-the-pi)** now, before
you flash the card, because two of the fixes have to be set up *during* the
build and cannot be added later without physical access.

The short version: **save your phone's hotspot as a WiFi network on the Pi.**
Then you are never locked out, because you control both ends.

---

## Part 1 — On the Mac: commit and push

Your Mac copy has work in it that has never been committed. If you skip this,
the fresh Pi gets an older robot than the one you have now.

### 1.1 See what's outstanding

Open Terminal and run:

```
cd /Users/michael/Projects/OhbotPi2
git status
```

As of 7 August 2026 that showed six modified files (`gui_server.py`,
`venue.py`, `knowledge.json`, `ohbot_chat.py`, `ohbotchat_server.py`,
`ohbotData/MotorDefinitionsv21.omd`) and several new ones that have never been
added — including `knowledge_base.py` and `clubhouse_knowledge.json`, which the
robot needs.

### 1.2 Add everything and commit

```
cd /Users/michael/Projects/OhbotPi2
git add -A
git commit -m "Clubhouse deployment: local knowledge base, venue prompt, robot profiles"
```

`git add -A` adds every changed and new file **except** the ones listed in
`.gitignore`. That exclusion is deliberate and correct — see
[Appendix A](#appendix-a--what-git-carries-and-what-it-doesnt).

### 1.3 Push

```
git push
```

If it asks for a password, that is GitHub wanting a Personal Access Token, not
your account password. Your existing `push_to_github.command` handles this —
double-click that instead if the plain `git push` gives you trouble.

### 1.4 Confirm it actually landed

Open <https://github.com/boquetebots/OhbotPi> in a browser and check that
`knowledge_base.py` and `clubhouse_knowledge.json` are listed. If they aren't,
the push didn't work and everything downstream will be wrong.

---

## Part 2 — Flash the SD card

Use **Raspberry Pi Imager** on the Mac.

### 2.1 Choices

| Setting | Value |
|---|---|
| Device | Raspberry Pi 4 |
| Operating System | Raspberry Pi OS **Lite** (64-bit) |
| Storage | your new SD card |

**Lite is the right choice, and it's what Yobot was built on (7 Aug 2026).**
The robot is headless — nobody ever looks at a desktop on it — so the full
image just adds hundreds of packages that need updating and can break.

Lite leaves out four things the robot needs. They're listed in
[Part 3.3](#33-install-the-four-missing-pieces) and take about three minutes
to add. That's the whole cost, and in exchange you get a leaner machine.

There's an unexpected bonus. The old Pi had a long-standing audio fault —
`aplay` failing with "error 524" — which forced everything through PipeWire.
On Lite there's no sound server grabbing the device, so plain ALSA works and
**PipeWire isn't needed at all**. Fewer moving parts than the old build.

**Use a good card.** A 32GB A2-rated card from SanDisk or Samsung. Cheap cards
are the single most common cause of a Pi that works for two weeks and then
doesn't.

### 2.2 The settings screen

When Imager asks *"Would you like to apply OS customisation settings?"* say
**Edit Settings**. This is the important screen.

**General tab:**

| Field | Value |
|---|---|
| Set hostname | `yobot1` |
| Username | `yobot` |
| Password | *(pick one and write it down — you cannot recover it)* |
| Configure wireless LAN — SSID | *your home lab WiFi name* |
| Wireless password | *your home lab WiFi password* |
| Wireless LAN country | `PA` |
| Set locale / timezone | `America/Panama` |
| Keyboard layout | `us` |

**Services tab:**

- ✅ **Enable SSH**
- Select **Use password authentication**

If you skip Enable SSH you will have to plug in a keyboard and monitor to fix
it. Don't skip it.

### 2.3 Write the card

Click Save, then Yes, then Yes again to confirm erasing. Takes about ten
minutes.

---

## Part 3 — First boot

1. Put the card in the Pi. **Leave the Ohbot USB cable unplugged for now** —
   one less thing to go wrong.
2. Power on. Wait a full **three minutes**. The first boot resizes the
   filesystem and reboots itself once. It looks frozen. It isn't.

### 3.1 Get in

From the Mac, in Terminal:

```
ssh yobot@yobot1.local
```

Type `yes` when it asks about authenticity, then your password.

**If the Mac says the host key has changed and refuses:** that's expected —
you had a different Pi at this name before. Clear the old record and retry:

```
ssh-keygen -R yobot1.local
ssh-keygen -R <your-pi-address>
```

**If `yobot1.local` isn't found at all,** jump to
[Part 9](#part-9--finding-the-pi).

### 3.2 Update everything

```
sudo apt update && sudo apt full-upgrade -y
```

Ten to twenty minutes. Then reboot and log back in:

```
sudo reboot
```

### 3.3 Install the four missing pieces

Lite leaves these out. All four are needed:

```
sudo apt install -y git espeak-ng python3-venv python3-dev
```

| Package | Why |
|---|---|
| `git` | To clone the project at all |
| `espeak-ng` | The offline voice that reads the IP address aloud |
| `python3-venv` | `install.sh` builds a virtual environment |
| `python3-dev` | `RPi.GPIO` is compiled from source and needs Python's headers. Without it `install.sh` dies with *"failed building wheel for RPi.GPIO"* — that's the wake button |

Then **check it worked**, because apt is silent on success:

```
which git espeak-ng
```

Two lines back means you're good. Nothing back means the install didn't run —
usually because the command was pasted before the SSH session was listening.
Run it again on its own and watch it finish.

### 3.4 Check the sound

Two separate devices, and they are not the same thing:

- **Speaker** — a powered speaker in the Pi's green 3.5mm jack. This is
  `card 0`, the built-in headphone output.
- **Microphone** — a USB mic. This is capture-only, so it will **not** appear
  in `aplay -l`. Use `arecord -l` to see it.

```
aplay -l      # should list card 0 Headphones, plus the two HDMI outputs
arecord -l    # should list your USB mic — note its card number
```

Test the speaker, first on the jack directly and then on the default route
that the robot's code actually uses:

```
speaker-test -D plughw:0,0 -t wav -c 2 -l 1
```

```
speaker-test -D plug:default -t wav -c 2 -l 1
```

You want to hear "front left, front right" both times. The second one matters
most — `plug:default` is what `yobot_core.py` falls back to when `pw-play`
isn't installed. If it works, you need no audio changes anywhere.

If the second one is silent, `default` is pointed at HDMI. Fix by creating
`/etc/asound.conf` with `defaults.pcm.card 0` and `defaults.ctl.card 0`.

---

## Part 4 — Install the project

### 4.1 Pull it down from GitHub

```
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/boquetebots/OhbotPi.git Ohbot
```

Note the `Ohbot` on the end — that renames the folder from `OhbotPi` to
`Ohbot`, which is what every script expects.

### 4.2 Plug in the Ohbot USB cable now

Then check the Pi can see it:

```
ls /dev/ttyACM* /dev/ttyUSB*
```

You should get one line back. If you get "No such file or directory", try the
other USB ports and a different cable.

### 4.3 Run the installer

```
cd ~/Projects/Ohbot
bash install.sh
```

This does the heavy lifting: virtual environment, all the Python packages, the
five systemd services, boot-without-login, the shutdown button permissions, and
the hardware watchdog. It asks for your OpenAI and Azure keys as it goes — have
them ready, or press Enter to skip and fill them in later.

It takes about ten minutes, mostly installing the Azure speech package.

Say **no** to the overlay filesystem question. That comes much later, in
[Part 10](#part-10--lock-it-down-last-step).

### 4.4 Install the IP announcer

```
cd ~/Projects/Ohbot
bash install_ip_announcer.sh
```

This makes the robot **say its own network address out loud** every time it
boots, and write it to the SD card. This is your insurance against exactly the
problem you hit yesterday. Say yes when it offers to test it — you should hear
the robot read out an address.

### 4.5 Fix the microphone

**Redo this any time you change the USB mic.** Swapping mics can change the
card number, and if `.env` points at the wrong one the robot simply stops
hearing anyone — with no error to tell you why.

> **Outstanding as of 7 Aug 2026:** the build was tested with a stand-in mic
> (an Anthem ARC-1) which happened to land on card 3, the same as the old Pi.
> Yobot's real mic is at the Library. When it's fitted, run `arecord -l`
> again and update `AZURE_MIC_DEVICE` to match.

Find out where it actually is:

```
arecord -l
```

You'll get something like:

```
card 2: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
```

The number after the word `card` is what you need. Add it to your keys file:

```
nano ~/Projects/Ohbot/.env
```

Add this line at the bottom, changing the `2` to whatever number you saw:

```
AZURE_MIC_DEVICE=plughw:2,0
```

Save with `Ctrl-O`, Enter, then `Ctrl-X`.

Check the speaker works too:

```
speaker-test -t wav -c 2 -l 1
```

---

## Part 5 — Copy the files git doesn't carry

Some files are kept off GitHub on purpose because the repo is public and they
contain passwords. **The robot still needs them.** Without
`library_knowledge.json`, Yobot cannot answer any question about the library —
hours, WiFi, the park, library cards, none of it.

On the **Mac**, in Finder, double-click:

```
/Users/michael/Projects/OhbotPi2/deploy_local_files.command
```

Press Enter to accept `yobot1.local`, or type the IP if you have it. It copies:

| File | Why it's not in git |
|---|---|
| `.env` | Your OpenAI and Azure API keys |
| `library_knowledge.json` | Contains the library's guest WiFi password and phone numbers |
| `ohbotData/active_robot.txt` | Which robot profile to load — machine-specific |
| `ohbotData/language.txt` | English or Spanish — machine-specific |

> **Note:** copying `.env` will overwrite the `AZURE_MIC_DEVICE` line you just
> added in step 4.5. Either run this step *first* and then fix the mic, or add
> the same `AZURE_MIC_DEVICE` line to the Mac's copy of `.env` so it travels
> with it. The second option is better — you only do it once.

### 5.1 Check the robot profile

The old Pi's active robot is `TallMan`. Confirm that's really the one going to
the Clubhouse, and that its file arrived:

```
cat ~/Projects/Ohbot/ohbotData/active_robot.txt
ls ~/Projects/Ohbot/ohbotData/robots/
```

You should see `TallMan.omd` in that folder. If the name in `active_robot.txt`
doesn't match a file in `robots/`, the motors will use factory defaults and the
face will look wrong.

---

## Part 6 — Add the Clubhouse WiFi (and your phone)

**Do not replace your home WiFi with the Clubhouse WiFi.** The Pi can remember
several networks and will join whichever one it can see. Adding the Clubhouse
as a *second* network means the robot works in both places with no fiddling —
and you keep a way back in.

### 6.1 Add your phone's hotspot — do this one first

This is the most valuable thing in this entire document. Turn on your phone's
personal hotspot, then on the Pi:

```
sudo nmcli device wifi connect "YOUR-PHONE-NAME" password "your-hotspot-password"
```

Test it, then reconnect to your home WiFi. Now, forever after, if you cannot
find the Pi anywhere: **turn on your phone hotspot, wait a minute, and the Pi
comes to you.** You control both ends, so no venue network can lock you out.

Set your phone hotspot's name and password to something you will not change.

### 6.2 Add the Clubhouse WiFi

Once you have the name and password:

```
sudo nmcli device wifi connect "CLUBHOUSE-WIFI-NAME" password "their-password"
```

If you're not physically there yet, you can add it blind so it's ready and
waiting:

```
sudo nmcli connection add type wifi con-name "Clubhouse" ifname wlan0 ssid "CLUBHOUSE-WIFI-NAME"
sudo nmcli connection modify "Clubhouse" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "their-password"
```

### 6.3 See what's saved, and set the pecking order

```
nmcli connection show
```

Higher priority numbers win when more than one network is in range:

```
sudo nmcli connection modify "YOUR-PHONE-NAME" connection.autoconnect-priority 100
sudo nmcli connection modify "Clubhouse" connection.autoconnect-priority 50
```

Giving your phone the highest priority means that when you switch the hotspot
on, the Pi hops off the venue network onto yours. That is a feature, not a bug
— it's your rescue lever.

---

## Part 7 — Test at home, thoroughly

Do all of this on your home lab WiFi, with the real robot, before you go
anywhere. It is much easier to fix things at your own desk.

Open `http://yobot1.local:5000` in a browser.

- [ ] Launcher page loads
- [ ] **Greeter** — starts, robot speaks a greeting
- [ ] Say hello — it hears you and answers
- [ ] Ask "what are the library hours?" — answers instantly, without an AI call
- [ ] Ask "what's the WiFi password?" — proves `library_knowledge.json` arrived
- [ ] Ask something open-ended — proves OpenAI is working
- [ ] Switch to Spanish, repeat the above
- [ ] Lips move in time with the speech
- [ ] **Stop the Greeter**, start **Sequence Builder** — status dot goes green
- [ ] All eight motors move from the sliders
- [ ] Load and play a saved sequence
- [ ] **Timeline** — opens, plays, playhead tracks
- [ ] "← Sequence Builder" link at the top of the Timeline works
      *(this was hardcoded to the old Pi's IP — now fixed)*
- [ ] **Calibration** page opens, shows TallMan's values
- [ ] Launcher **Shutdown** and **Restart** buttons work
- [ ] Language toggle changes all four pages

### 7.1 The power-cut test

This matters — kids will unplug it.

1. With the Greeter running, pull the power cord out of the wall.
2. Wait ten seconds. Plug it back in.
3. It should boot, **say its address out loud**, and the Launcher should come
   back on its own.
4. Do this five times. Any corruption or hang shows up here, not later.

### 7.2 The overnight test

Leave it running overnight with the Greeter on. Next morning, talk to it. Bots
that work for an hour and die after six are a real thing — usually a memory
leak or a dropped WiFi connection that never reconnects.

---

## Part 8 — SAMBA (optional, do it last)

`install.sh` does **not** set up SAMBA. Without it you lose
`/Volumes/Projects/Ohbot` on the Mac and have to use `scp` for everything.

On the Pi:

```
sudo apt install samba samba-common-bin -y
sudo nano /etc/samba/smb.conf
```

Go to the very bottom and add:

```
[Ohbot]
   path = /home/yobot/Projects/Ohbot
   browseable = yes
   writeable = yes
   create mask = 0644
   directory mask = 0755
   valid users = yobot
```

Save (`Ctrl-O`, Enter, `Ctrl-X`), then set a share password and restart it:

```
sudo smbpasswd -a yobot
sudo systemctl restart smbd
```

On the Mac: Finder → Go → Connect to Server → `smb://yobot1.local/Ohbot`

Note this changes your mount path from `/Volumes/Projects/Ohbot` to
`/Volumes/Ohbot`. Anything on the Mac that refers to the old path — including
`sync_pi_from_github.command`, which still has `/home/michael` in it — needs
updating.

---

## Part 9 — Finding the Pi

You could not find it yesterday. Here is every method, best first. The first
two need no cooperation from the venue network at all.

### Method 1 — Turn on your phone's hotspot

If you did step 6.1, this is the whole answer. Switch on the hotspot, wait
about a minute for the Pi to notice and join, connect your Mac to the same
hotspot, then:

```
ssh yobot@yobot1.local
```

Both devices are on a network you own. Nothing the library does can block it.

### Method 2 — Listen to the robot

About thirty seconds after you plug it in, Yobot says its own address out loud,
twice, slowly, digit by digit. Write it down and use it directly:

```
http://192.168.1.47:5000
```

If it says *"I could not join a wireless network,"* that's your answer — the
WiFi name or password is wrong, and no amount of scanning will find it.

### Method 3 — Read the SD card

If the Pi is unplugged: pull the SD card, put it in your Mac. A small disk
called `bootfs` appears. Open **YOBOT_IP.txt** on it. That's the address it had
last time it ran, plus which WiFi network it joined.

### Method 4 — Direct Ethernet cable

Run a plain Ethernet cable from the Pi straight to the Mac (you'll need a
USB-C-to-Ethernet adapter). No router, no switch, no WiFi. Both ends give
themselves an address automatically and can see each other:

```
ssh yobot@yobot1.local
```

Keep a cable and adapter in the robot's bag. This has never failed me.

### Method 5 — Ask the venue for a fixed address

Ask whoever runs the library's network for a **DHCP reservation** for the Pi.
Give them its MAC address, which you can get on the Pi with:

```
ip link show wlan0 | grep ether
```

Then the Pi gets the same address every single time and you can write it on a
label and stick it to the robot's base. This is the proper long-term fix.

### Method 6 — Scan from the Mac

Last resort, and often blocked. On the Mac:

```
arp -a
```

Look for entries starting `b8:27:eb`, `dc:a6:32`, `e4:5f:01`, or `d8:3a:dd` —
those are Raspberry Pi hardware. Or install `nmap` and sweep the range:

```
nmap -sn 192.168.1.0/24
```

### Why `yobot1.local` fails on venue networks

The `.local` name works by shouting "who is yobot1?" to everyone on the network
and waiting for an answer. Many public, guest, and school networks turn on
**client isolation**, which stops devices talking to each other at all — partly
for security, partly to stop people snooping. On such a network `yobot1.local`
can never work, no matter what you do, and neither can opening
`http://<ip>:5000` from a laptop on the same WiFi.

**If the Clubhouse network has client isolation, the robot will still work
perfectly** — it talks outward to OpenAI and Azure, which is allowed. You just
won't be able to reach its web pages from a laptop on that network. That is
what your phone hotspot and the Ethernet cable are for.

---

## Part 10 — Lock it down (last step)

Only once everything has worked at the Clubhouse for a week or so.

The overlay filesystem makes the SD card read-only, so a yanked power cord can
never corrupt it. On the Pi:

```
sudo raspi-config nonint do_overlayfs 1
sudo reboot
```

**Understand the trade-off first.** With overlay on, *nothing* you change
survives a reboot. New sequences, calibration tweaks, edited knowledge files,
`apt` updates — all gone at the next power cycle. To make a change you turn it
off, reboot, make the change, turn it on, reboot again:

```
sudo raspi-config nonint do_overlayfs 0
sudo reboot
```

Do this when you are finished tinkering, not before.

---

## Appendix A — What git carries, and what it doesn't

### Git carries

All the Python code, all four web pages, `i18n.js`, `knowledge.json` (Yobot's
identity), `clubhouse_knowledge.json`, the robot profiles in
`ohbotData/robots/`, `MotorDefinitionsv21.omd`, `install.sh`, and
`requirements.txt`.

### Git does not carry — and why

| File | Reason | How it gets there |
|---|---|---|
| `.env` | API keys | `install.sh` prompts, or `deploy_local_files.command` |
| `library_knowledge.json` | Contains the library's guest WiFi password and phone/WhatsApp numbers, and the repo is public | `deploy_local_files.command` |
| `ohbotData/active_robot.txt` | Machine-specific — sharing it would let the Mac overwrite the Pi's choice | `deploy_local_files.command` |
| `ohbotData/language.txt` | Machine-specific | `deploy_local_files.command` |
| `CLAUDE.md`, `HANDOFF_*.md` | Your working notes, not for the public repo | Stay on the Mac — the Pi doesn't need them |
| `venv/` | Rebuilt from `requirements.txt` | `install.sh` |

**If you would rather have everything in one place,** the alternative is to
make the GitHub repo private and commit `library_knowledge.json` along with
everything else. That removes the manual copy step, at the cost of the repo no
longer being shareable. Both are reasonable — just pick one on purpose.

---

## Appendix B — Things that changed for this build

Fixed on 7 August 2026 while writing this:

- **`gui/timeline.html`** had `http://<your-pi-address>:5001/gui` hardcoded in the
  "← Sequence Builder" link. Now a relative link, so it works on any Pi.

- **`push_to_github.command`** was rewritten. The old one had a *fixed list of
  files* and a *hardcoded commit message* left over from one day's work in
  August. It would have silently skipped `knowledge_base.py`,
  `clubhouse_knowledge.json`, `venue.py` and the chat servers — the entire
  Clubhouse build — while claiming success. It now picks up everything, asks
  you for a message, and refuses to push if a secret file ever ends up staged.

- **`sync_pi_from_github.command`** was rewritten. The old one had the previous
  Pi's username baked in, plus one-time repair surgery from the August 3rd
  reconciliation (a fixed list of files to discard) that no longer applies to a
  fresh clone. It now asks which Pi, warns you if the SD card is in read-only
  overlay mode, shows you any Pi-side changes before touching them, and offers
  to restart the services.

- **Four calibration scripts** had `/home/michael/Projects/Ohbot` in their help
  text. Now `~/Projects/Ohbot`, which is correct for any username.

Found and fixed during the actual build, same day:

- **`install.sh` never created the `ohbot-calibration` service.** It made four
  of the five the project needs. On the old Pi that service had been created
  by hand years ago and never written down, so this only surfaced on the first
  genuinely fresh build — the Launcher's Calibration button opened a page that
  nothing was serving. Now installed with the rest.

- **`install.sh` wiped `AZURE_MIC_DEVICE` on every re-run.** It rewrites
  `.env` from a fixed template containing only the three API keys, so any
  other setting vanished. Since re-running the installer is the normal way to
  pick up changes, this was a trap waiting to spring: the robot would go deaf
  and nothing would say why. It now preserves any settings it doesn't manage.

- **`deploy_local_files.command` could never connect.** It used
  `BatchMode=yes`, which means "never ask for a password" — so with no SSH key
  set up it failed every time regardless of the address. Both it and
  `sync_pi_from_github.command` now share one connection and ask once.

Still worth cleaning up some day, not urgent:

- `install.sh` finishes by telling you to open `ohbot.local:5000`. It's
  `yobot1.local:5000` now.
- `gui/index.html` line 732 has `http://localhost:5000` as the Launcher link,
  but JavaScript overrides it with the right address, so it works.

The good news: **`install.sh` is already username-proof.** It uses `$HOME` and
`whoami` everywhere, so changing from `michael` to `yobot` needs no code edits
at all.

---

## The very short version

This is the route that actually worked on 7 August 2026. Run the Pi commands
**one at a time** — pasting a block means the first few are swallowed before
the SSH session is listening, which cost us two false diagnoses.

```
# On the Mac
double-click push_to_github.command

# Flash card: PiOS Lite 64-bit, hostname yobot1, user yobot, home WiFi, SSH on

# On the Pi
ssh yobot@yobot1.local
sudo apt update && sudo apt full-upgrade -y && sudo reboot
sudo apt install -y git espeak-ng python3-venv python3-dev
which git espeak-ng                     # confirm — apt is silent on success
aplay -l ; arecord -l                   # speaker on card 0, USB mic elsewhere
speaker-test -D plug:default -t wav -c 2 -l 1
mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/boquetebots/OhbotPi.git Ohbot
ls /dev/ttyACM*                         # brain board present?
cd Ohbot && bash install.sh             # skip keys, say NO to overlay
bash install_ip_announcer.sh
sudo nmcli device wifi connect "YOUR-PHONE-HOTSPOT" password "..."

# On the Mac
double-click deploy_local_files.command
ssh-copy-id yobot@yobot1.local           # optional: no more passwords

# On the Pi, only when the real mic is fitted
arecord -l                              # note the card number
nano ~/Projects/Ohbot/.env              # set AZURE_MIC_DEVICE=plughw:N,0

# Then test everything in Part 7 before you go anywhere.
```
