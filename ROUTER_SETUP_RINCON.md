# Router Setup — RinconClubhouse

**Built and tested at home 2026-08-07. Working.**

Hardware: **TP-Link Archer C64** (primary). Linksys EA4500 in the bag as a spare.

---

## What This Does

The clubhouse has a live Ethernet drop in the wall. You plug your own router into
it, and that router creates a WiFi network you control.

Why this beats joining the venue's own WiFi: library and clubhouse networks are
usually **captive portals** — the kind with an "I Agree" page. A headless robot
can't click that button. Your own router on the wired drop never sees a portal.

You've done this before at the library for the Boquete photo club.

---

## As-Built Configuration

Deliberately minimal. Everything left at factory defaults except the WiFi name
and password.

| Setting | Value |
|---------|-------|
| Router admin page | `http://192.168.0.1` |
| WiFi network name | `RinconClubhouse` |
| Router LAN range | `192.168.0.x` (TP-Link default — unchanged) |
| Pi's address on it | `192.168.0.101` (assigned by DHCP, not reserved) |
| Pi's SSH login | `yobot@` |
| Pi's hostname | `pibot` → `pibot.local` |

**There is no fixed IP address for the Pi and that's on purpose.** An earlier
draft of this plan pinned it to `192.168.50.155` to match the home network. That
was dropped — it added three ways to fail and bought nothing, because you don't
need to know the address. See "Finding the Pi" below.

---

## Finding the Pi — Three Ways, Any One Is Enough

1. **It says its address out loud.** About a minute after boot, the robot speaks
   its own IP through its speaker (`announce_ip.py`). Uses espeak-ng, not the
   Azure voice, so it works with no internet at all.
2. **By name:** `ssh yobot@pibot.local` — avahi is running on the Pi and this
   works on any network, whatever address it got.
3. **The router's client list:** `http://192.168.0.1` → **Network Map** or
   **Clients**. This is ground truth — it doesn't depend on anything on the Pi
   working.

None of the web tools hardcode an address. The Launcher binds to all interfaces
and `gui/index.html` builds its links from `location.hostname` at runtime, so
every page works at whatever address the Pi lands on.

---

## ⚠️ Power-On Order Matters

**Power the router FIRST. Wait 2–3 minutes. THEN boot the Pi.**

This is the one thing that went wrong during setup, and it cost an hour.

The Pi checks which networks are in the air at the moment it boots and picks the
best one it can *see*. If the router is still starting up, the Pi doesn't hear
`RinconClubhouse` at all, shrugs, and joins whatever else is around. It won't
retry on its own.

Priority settings don't help. Priority only ranks networks the Pi can already
hear — it can't rank one that wasn't broadcasting yet.

**Symptom:** the robot announces the wrong address. **Fix:** reboot the Pi with
the router already up and settled.

---

## How the Pi Chooses

On the Pi, `RinconClubhouse` is a NetworkManager profile at
**autoconnect-priority 10**. Home WiFi (`netplan-wlan0-LIB-8892629_EXT`) sits at
`0`.

So the Pi prefers the clubhouse network whenever it can hear it, and falls back
to home WiFi by itself when it can't. That fallback is deliberate — it means a
wrong password or a dead router can never strand a headless Pi with no way in.

To inspect it:

```
nmcli -f NAME,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show
```

---

## At the Clubhouse

1. Plug an Ethernet cable from the **wall jack** to the router's **blue WAN
   port**.
2. **Power the router on. Wait 2–3 minutes.** Don't rush this — see above.
3. Join the **Mac** to `RinconClubhouse`. Load any website to prove the wall jack
   is actually feeding internet.
4. **Now** power up the Pi.
5. Listen for the announced address, or just:

```
ssh yobot@pibot.local
```

6. Confirm the Pi has internet:

```
ping -c 3 1.1.1.1
ping -c 3 api.openai.com
```

**Both must work or Yobot will be silent.** The first tests raw internet; the
second also tests name lookup.

7. Open the Launcher at `http://pibot.local:5000/` and start the Greeter.

---

## Troubleshooting

### The Mac has no internet after plugging into the wall jack

`http://192.168.0.1` → **Advanced → Network → Internet** and read the status.

- **No WAN address** — the jack may be dead or the far-end port switched off.
  Try another jack.
- **Has an address but no internet** — load any website on the Mac. If a login
  page appears, click through it; the whole network comes with you.
- **Still nothing** — swap in the Linksys EA4500. Known to work in that building.

### The robot announces the wrong address

It booted before the router was ready. Reboot the Pi. That's almost always it.

### The Pi doesn't appear at all

Check the router's client list first — that tells you whether it's a Pi problem
or a network problem.

If it's genuinely not joining, get to it another way and check what it can hear:

```
sudo nmcli device wifi rescan
sleep 5
nmcli -f SSID,BSSID,CHAN,SIGNAL,SECURITY device wifi list
```

If `RinconClubhouse` isn't listed, the Pi can't hear the router — move it closer
or check the router is actually broadcasting. If it *is* listed, the saved
password is wrong:

```
sudo nmcli connection modify RinconClubhouse wifi-sec.psk "CORRECT_PASSWORD"
```

### pibot.local doesn't resolve

Use the address the robot announced, or the one in the router's client list.

### Yobot won't speak, but the network is fine

```
systemctl --user status ohbot-server ohbot-conversation --no-pager
```

No `sudo` — these are **user** services and only exist inside a `yobot` session.

---

## Dead End — Don't Revisit

The **Cable Matters 201014** USB-C multiport adapter cannot do Ethernet on the
MacBook Air. It uses an **ASIX AX88179** chip with no macOS driver, and Cable
Matters' only fix is permanently disabling System Integrity Protection to install
a 2021-era beta driver. Not worth it.

If a USB-C Ethernet dongle is ever needed, buy one with a **Realtek RTL8153 or
RTL8156** chipset — those need no driver on macOS. Avoid ASIX.

---

## Pack List

- [ ] TP-Link Archer C64 + power supply
- [ ] Linksys EA4500 + power supply (spare)
- [ ] Two Ethernet cables
- [ ] Raspberry Pi + power supply
- [ ] MacBook + charger
- [ ] Ohbot USB cable
- [ ] Speaker and microphone
- [ ] Router admin password + WiFi password, written down
- [ ] This document
