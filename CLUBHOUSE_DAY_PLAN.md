# Clubhouse Day Plan — Getting Into the Pi With No Known WiFi

**Written 2026-08-07 for the library clubhouse visit on 2026-08-08.**

The problem: the Pi is headless, you don't have the clubhouse WiFi name or
password, and library WiFi is often a captive portal that a screenless robot
can't click through.

The plan: use your MacBook as the Pi's doorway. The Mac has a screen, so it can
click "I Agree" on the portal. Then the Mac shares that internet down an
Ethernet cable to the Pi. One setup solves all three problems — terminal access,
internet for Yobot, and the portal.

---

## Part 1 — Buying the Adapter (morning, before you go)

### What died

The old **Cable Matters 201014** multiport adapter uses an **ASIX AX88179**
Ethernet chip. macOS has no built-in driver for it. Cable Matters' own fix is to
boot into Recovery Mode, permanently disable System Integrity Protection, and
install a beta driver last updated in 2021. Don't do this. It probably won't work
on an Apple Silicon Mac anyway.

### What to buy

Ask for a **USB-C to Gigabit Ethernet adapter that works on a Mac with no driver
install.**

- **Chipset to look for:** Realtek **RTL8153** (gigabit) or **RTL8156** (2.5 gig).
  Both are supported by macOS out of the box.
- **Chipset to avoid:** ASIX **AX88179**. That's what just failed you.
- **Safe brands:** Belkin, Anker, UGREEN, CalDigit, OWC, Satechi, TP-Link UE300C.
- **Get the plain single-purpose dongle** — USB-C on one end, Ethernet jack on
  the other. Not a multiport hub. Fewer parts, fewer ways to fail.

### Red flags in the shop

- Comes with a mini driver CD → walk away.
- Box says "driver required for Mac" or "Mac driver download" → walk away.
- Dusty old stock with a faded box → likely the old ASIX generation.

### Test it before you leave the shop

Ask to open it and plug it into your MacBook. Then:

1. Open **System Settings → Network**.
2. A new entry should appear on its own within a few seconds — something like
   "USB 10/100/1000 LAN".

**If it appears without you installing anything, it's the right adapter.** If
nothing appears, hand it back and try another brand.

If they'll let you run a command, this confirms it:

```
system_profiler SPUSBDataType | grep -i -B2 -A6 "ethernet\|LAN\|RTL\|Realtek"
```

Any output at all means the Mac sees it.

### Also buy

A **short Ethernet cable** if you don't have one in the bag. Any Cat5e or Cat6
patch cable. Crossover cables are not needed — modern gear sorts itself out.

---

## Part 2 — At the Clubhouse

### Step 1 — Get your Mac online first

Join the clubhouse WiFi on the **Mac**. If a login page pops up, click through
it. Confirm you actually have internet by loading a website.

Write down the WiFi name and password while you're at it — you'll want them
later.

### Step 2 — Connect the Pi to the Mac

Plug the new adapter into the Mac, and an Ethernet cable from the adapter to the
Pi. Power up the Pi.

Check for **link lights** at the Pi's Ethernet jack. Lights = the cable link is
alive. No lights = go to Troubleshooting below.

### Step 3 — Turn on Internet Sharing

On the Mac:

1. **System Settings → General → Sharing**
2. Find **Internet Sharing** in the list. Click the small **ⓘ** button next to it
   (don't flip the switch yet).
3. **Share your connection from:** `Wi-Fi`
4. **To devices using:** tick the box for your Ethernet adapter
5. Click **Done**, then flip the **Internet Sharing** switch **on**
6. Confirm when it asks

The Internet Sharing icon appears in the menu bar when it's running.

### Step 4 — Get in

Wait about 30 seconds for the Pi to pick up an address, then in **Terminal**:

```
ping -c 3 yobot1.local
```

Replies mean you're in. Then:

```
ssh yobot@yobot1.local
```

### Step 5 — Confirm the Pi has internet

Once you're SSH'd in, on the Pi:

```
ping -c 3 1.1.1.1
```

That tests raw internet. Then:

```
ping -c 3 api.openai.com
```

That tests name lookup too. **Both must work or Yobot will be silent.**

### Step 6 — Add the clubhouse WiFi to the Pi (optional)

Now that you're in, you can teach the Pi the clubhouse network so it doesn't
need the cable:

```
sudo nmcli device wifi connect "THEIR_NETWORK_NAME" password "THEIR_PASSWORD"
```

⚠️ **Warning:** this kicks the Pi's WiFi over to their network. If that network
has a captive portal, the Pi will be *connected* but have *no internet*, and
Yobot still won't talk. **The Ethernet cable is the reliable path — leave it
plugged in.** Only do this step if you've confirmed there's no portal.

---

## Part 3 — If the Adapter Route Fails

### Backup: iPhone Personal Hotspot

No cable, no adapter, no portal.

1. Turn on **Personal Hotspot** on the iPhone.
2. Join the **Mac** to it.
3. The Pi joins it automatically *if it was set up in advance* — see the setup
   doc. If it wasn't set up in advance, this won't work, which is why it's worth
   doing tonight.
4. `ssh yobot@yobot1.local`

This also gives Yobot real internet over cell data, with no portal to click.
API calls are text and short audio — very little data.

> **Status: not yet configured.** Ask Claude to walk through the hotspot setup
> before you leave.

---

## Troubleshooting

### No link lights at the Pi's Ethernet jack

- Is the Pi actually powered on? Its own LEDs lit?
- Re-seat both ends of the Ethernet cable until they click.
- Try the Mac's other USB-C port.
- Plug the adapter straight into the Mac, not through a hub or the monitor.
- Try a different Ethernet cable.

### Lights, but `ping yobot1.local` fails

The Pi's name may not be resolving. Find it by address instead:

```
arp -a
```

Look for a line with an address starting `192.168.2.` — that's the Pi on the
shared connection. Then:

```
ssh yobot@192.168.2.2
```

(substituting whatever address you found).

### Mac shows "Self-Assigned IP" on the Ethernet port

Normal and fine when Internet Sharing is off. Once Internet Sharing is on, the
Mac becomes the router and hands the Pi an address.

### Pi connects but Yobot doesn't speak

Almost certainly no internet reaching the Pi. Re-run Step 5. If `ping 1.1.1.1`
works but `ping api.openai.com` fails, it's a DNS problem — tell Claude.

### The robot won't respond to the mic

Different problem entirely. Check that the right services are running:

```
systemctl --user status ohbot-server ohbot-conversation --no-pager
```

No `sudo` — these are user services.

---

## Pack List

- [ ] Raspberry Pi + power supply
- [ ] New USB-C Ethernet adapter (tested in the shop)
- [ ] Ethernet cable
- [ ] MacBook + charger
- [ ] iPhone (hotspot backup)
- [ ] Ohbot USB cable
- [ ] Speaker and microphone
- [ ] This document
