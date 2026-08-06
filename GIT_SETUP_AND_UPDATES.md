# Getting Ohbot Updates from GitHub

This covers two things: getting the project onto your Pi for the first time using git, and pulling future updates (like the new Timeline editor) once you have it.

If you already have Ohbot running and just want the update, skip to **Part 2**.

---

## Part 1 — Install git and get the project (first time only)

Open a terminal to run these commands one at a time — either SSH into your Pi from another computer, or, if you're using the Pi's own desktop with a monitor/keyboard, open the **Terminal** app (black icon in the taskbar, or find it in the menu under Accessories).

**1. Install git** (most Raspberry Pi OS installs already have it — this command is safe to run either way):

```bash
sudo apt update
sudo apt install git -y
```

**2. Create the project folder and go into it:**

```bash
mkdir -p ~/Projects/Ohbot
cd ~/Projects/Ohbot
```

**3. Download the project:**

```bash
git clone https://github.com/boquetebots/OhbotPi.git .
```

(That trailing `.` matters — it tells git to put the files directly in the folder you're already in, instead of creating a new subfolder.)

**4. Run the installer:**

```bash
bash install.sh
```

It'll ask for your API keys and set everything up to start automatically. Full details on that step are in `INSTALL_GUIDE.md` in the project itself if you get stuck.

---

## Part 2 — Get future updates

Whenever there's a new update (like this one — the Sequence Builder and Timeline are now combined into one), run this on your Pi:

```bash
cd ~/Projects/Ohbot
git pull origin main
sudo systemctl restart ohbot-gui
```

What each line does:
- `cd ~/Projects/Ohbot` — go to the project folder
- `git pull origin main` — download whatever's changed on GitHub since you last updated
- `sudo systemctl restart ohbot-gui` — restart the Sequence Builder program so it actually starts using the new files (without this, the new files are downloaded but the old version keeps running until the Pi reboots)

That's it — no need to reinstall anything or re-enter your API keys.

---

## If `git pull` complains about local changes

This means a file was edited directly on your Pi at some point and git doesn't want to overwrite it. If you haven't intentionally changed anything yourself, it's safe to discard those changes and take the GitHub version:

```bash
git reset --hard origin/main
```

**Warning:** this throws away any of your own edits to the project's code files. It does NOT touch your saved sequences or your `.env` file with your API keys — those are safe either way.
