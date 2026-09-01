# Yobot on Windows

Yobot is a robot head that listens, thinks and talks back. This guide gets it
running on a Windows laptop.

You need:

- A Windows laptop
- Yobot, its power supply, and its USB cable
- Internet — Yobot's voice and brain live online
- A free **Microsoft Azure** account, for the voice — see Step 4
- An account with **one** AI company, *only* if you want Yobot to hold a
  conversation. Several will do, and Step 4 lists them

Nothing here needs the Raspberry Pi, and you don't need to know any code.

---

## What you are setting up

**One installation.** This project is Yobot itself — the motors, the voice, the
moving mouth, and a control panel you drive from a web browser. Everything
below sets that up, and it is the same for everybody.

Two things sit on top of it. Neither changes the install:

- **Chess.** A second project that borrows this one's voice and motors so
  Yobot can play a game out loud against a guest. Add it whenever you like —
  there is a short section near the end of this page. It asks for no account
  of its own.
- **Conversation.** Yobot listening and talking back. The code is already
  here; it needs one AI account to switch on, and Step 4 says how. You can add
  that later without redoing anything.

**Azure is the one account you actually need**, because Azure is the voice.
Without it Yobot still moves — it just does it in silence.

---

## Step 1 — Get the Yobot files

Two ways. Either is fine.

**From GitHub** — always the newest version:

1. Go to **https://github.com/boquetebots/OhbotPi**
2. Click the green **Code** button, then **Download ZIP**
3. Find the ZIP in your Downloads, right-click it → **Extract All**
4. Put it at **`C:\Projects\OhbotPi2`** — make the `C:\Projects` folder
   first if it is not there, then **rename** the extracted folder from
   `OhbotPi-main` to `OhbotPi2`

No account needed, and nothing to install.

> **Why that exact place?** The chess project finds this one by looking in the
> folder next door, so `C:\Projects\OhbotPi2` sitting beside
> `C:\Projects\Chess` means there is nothing to configure. Even if you never
> add chess, putting it there costs nothing and saves moving it later.

**From the ZIP Michael sent you** — download it, right-click → **Extract All**,
and put the folder at `C:\Projects\OhbotPi2` in the same way.

> ⚠️ **Extract the ZIP properly.** Windows lets you peek inside a ZIP as
> though it were a folder, and things half-work if you run Yobot from in
> there. Right-click → **Extract All** first, then work in the real folder.

---

## Step 2 — Install Python

Yobot is written in Python, so the laptop needs it.

Go to **https://www.python.org/downloads/** and click the big yellow download
button.

> ⚠️ On the **first screen** of the installer, tick
> **"Add python.exe to PATH"** before clicking Install.
> It's a small box near the bottom and it's easy to miss. Without it, nothing
> else in this guide works.

That's the only decision in the whole installer. Everything else, click through.

---

## Step 3 — Set Yobot up

Open the Yobot folder, go into the **`Windows`** folder, and
**double-click `SETUP.bat`**.

> Everything you ever need to double-click on Windows lives in that one
> folder. You can ignore the rest of the project.

A black window opens and installs everything Yobot needs. It takes a few
minutes — the speech package is a big one. Let it finish.

When it's done it tells you whether anything is still missing. Expect it to
say `.env` is missing — that's Step 4.

---

## Step 4 — Get your keys

Yobot's voice and its brain are online services. They need your own accounts —
the files you downloaded deliberately don't include anybody's keys.

They have free or very cheap tiers. Light use costs pennies.

**You need the Azure one.** It is the voice. Without it Yobot moves in
silence, and chess has nothing to speak with either.

**The brain is optional, and it can wait.** It is what lets Yobot hold a
conversation. Nothing else uses it — not the motors, not the control panel,
not chess.

**Microsoft Azure — the voice and the listening**

1. Sign up at **https://azure.microsoft.com/free**
2. In the Azure portal, create a **Speech** resource (search "Speech" and
   follow the prompts — the free tier is fine)
3. Once it's made, open it and find **Keys and Endpoint**
4. Copy **KEY 1** and note the **Location/Region** (something like `eastus`)

**The brain — the conversation** *(optional; the one that can wait)*

Yobot is not tied to one AI company. Pick **one** of these, get a key from it,
and that is the whole job:

| Company | Where the key comes from | Worth knowing |
|---|---|---|
| **OpenAI** | platform.openai.com → API keys | The default, and what Yobot has always used. |
| **Anthropic** | console.anthropic.com → API keys | Claude. |
| **Google Gemini** | aistudio.google.com/apikey | Has a free tier. |
| **Groq** | console.groq.com → API keys | Runs open models on its own hardware — fast, and very cheap. |
| **Ollama** | nothing to sign up for | Runs on your own computer or network. No account, no bill, and the thinking never leaves the building. |

Whichever you pick: copy the key the moment it appears — most are shown once —
and expect to put a small amount of credit on the account.

**Put them in the file**

In the **main** Yobot folder — one level up from `Windows` — there's a file
called **`.env.example`**. Make a copy of
it, and rename the copy to exactly **`.env`** — no `.example`, no `.txt`.
Open it in Notepad and fill in your two Azure values:

```
AZURE_SPEECH_KEY=the key you copied from Azure
AZURE_SPEECH_REGION=eastus
```

Save it. **That is a complete, working file.** With those two lines Yobot
moves, speaks, and plays chess.

**Switching the conversation on** is two more lines — which company, and its
key:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=the key you copied
```

Swap in whichever you chose: `anthropic` with `ANTHROPIC_API_KEY`, `gemini`
with `GEMINI_API_KEY`, `groq` with `GROQ_API_KEY`, or `ollama`, which needs no
key at all. Leave `LLM_PROVIDER` out and Yobot assumes OpenAI, exactly as it
always did. `.env.example` lists every one of them with its web address.

**Or skip this file entirely.** The Launcher page has a **Settings & Keys**
link that does all of the above in the browser, and can test each key for you.
It is described under *Using Yobot* below. Editing `.env` by hand still works
and is how it has always been done.

> ⚠️ **Windows hides file extensions**, and this is exactly where it bites.
> A file that shows as `.env` may really be `.env.txt`, and Yobot won't find
> it. In File Explorer turn on **View → Show → File name extensions**, then
> check the name is just `.env`.

Keep these keys to yourself — anyone who has them can spend your money.

Run `SETUP.bat` again and it should now report `.env` as found.

---

## Step 5 — The motor settings file

Each robot's motors are slightly different, so each has its own settings file,
ending in **`.omd`**. It goes in the **`ohbotData`** folder, in the main Yobot
folder.

- **If Michael set up your robot**, ask him for its `.omd` file and drop it in
- **If your robot has never been calibrated**, skip this for now. Yobot will
  still move, just on generic settings — it says so when it starts. You can
  calibrate it later from the Motor Calibration page.

---

## Step 6 — Plug Yobot in and test it

1. Plug the USB cable into the laptop
2. Switch Yobot's power supply on
3. **Double-click `yobot-test.bat`**

Yobot should turn its head, nod, blink, open its mouth, and change eye colour.

**If that worked, you're done setting up.**

If it says *Robot not found*, see Troubleshooting at the end.

---

## Using Yobot

**Double-click `yobot-launcher.bat`.**

A black window opens and your web browser opens a page with buttons. That page
is the remote control. Leave the black window alone — closing it switches Yobot
off.

The page offers three things, and **only one can run at a time** because they
all share the single USB cable:

| Button | What it does |
|--------|-------------|
| **Greeter** | The conversation. Yobot listens, replies out loud, and moves as it talks. |
| **Sequence Builder** | Design your own movements and play them back. |
| **Motor Calibration** | Fine-tune each motor's limits. Only needed occasionally. |

Press **Stop** before switching to a different one — or just press the one you
want and it'll swap over for you.

### The Settings page

There is a **`⚙ Settings & Keys`** link on that same page, and it is the easy
way to handle everything in Step 4. It lets you paste your Azure key, choose
which AI company the brain uses, pick a model, and press a button that checks
each one actually answers — all in the browser, with no Notepad and no hunting
for hidden file extensions.

Anyone on the same WiFi can open the Launcher, so the first time you use
Settings it offers to set a password. Until you set one it stays unlocked, so
that a fresh install cannot lock you out of the page you need to set it from.

### Talking to Yobot

Start the **Greeter** and a second black window opens. That's Yobot's own
window — it shows what it heard and what it's saying.

Just talk to it. It replies.

If nobody speaks for a while, Yobot dozes off to save money on the speech
service. To wake it: click **Wake** on the web page, or press **Enter** in
Yobot's own window.

### Finishing up

Press **Stop** on the web page, then close the black windows.

If a window won't close or something seems stuck, **double-click
`yobot-stop.bat`** — it shuts down anything Yobot left running.

---

## The Four Buttons, In Short

All four are in the **`Windows`** folder.

| Double-click this | To do this |
|-------------------|-----------|
| `SETUP.bat` | Set Yobot up. Once, at the start. |
| `yobot-test.bat` | Check the robot moves. Any time something seems off. |
| `yobot-launcher.bat` | **Use Yobot.** This is the everyday one. |
| `yobot-stop.bat` | Shut everything down if it gets stuck. |

---

## Adding chess

The chess show is a second project that borrows this one's voice and motors.
Once `yobot-test.bat` works, it is a short hop:

1. Go to **https://github.com/boquetebots/YobotChess**
2. Green **Code** button, then **Download ZIP**, and extract into `C:\Projects`
3. **Rename** the folder from `YobotChess-main` to `Chess`, so you have
   `C:\Projects\Chess` sitting beside `C:\Projects\OhbotPi2`
4. Open **`START HERE - Windows.md`** inside it and follow that

It asks for no keys of its own. It uses the Azure voice you set up in Step 4,
and it never touches the conversation key.

---

## Troubleshooting

**"Robot not found"**

1. Unplug the USB cable, count to five, plug it back in
2. Check Yobot's power supply is actually on
3. Try `yobot-test.bat` again

Still stuck? Open PowerShell in the `Windows` folder and run `.\yobot.bat ports`.
That lists what the laptop can see. If **nothing** is listed, Windows is
missing the driver for Yobot's controller board — open **Device Manager** and
look for a yellow warning triangle. The name beside it tells you which driver
to search for, usually **CH340** or **CP210x**. That's a one-time install.

**No sound**

Check the laptop isn't muted, and that the right speaker is chosen in
**Settings → System → Sound**. Yobot uses whatever Windows is set to.

Bluetooth speakers work but lag slightly, so the mouth movements drift out of
step with the voice. A wired speaker, or the laptop's own, looks better.

**Yobot talks but doesn't hear you**

Check **Settings → System → Sound → Input** — speak, and the level bar should
move. Then check **Settings → Privacy & security → Microphone** and make sure
desktop apps are allowed to use it.

**Windows asks about the firewall the first time**

Click **Allow access**. Private networks is enough. Yobot's control page runs
as a small local website, which is why Windows asks.

**"Python is not recognized"**

Python was installed without the PATH box ticked. Re-run the Python installer,
choose **Modify**, and tick it. Then run `SETUP.bat` again.

**The first word of each sentence sounds clipped**

Should already be handled — Yobot adds a moment of silence before speaking,
because Windows powers the speaker down when idle and swallows the first
fraction of a second. If it still happens on your laptop, open `.env` in
Notepad and add this line, raising the number until it's clean:

```
AUDIO_LEAD_IN_MS=550
```

---

## One Last Thing

Only one computer can drive Yobot at a time — they'd fight over the cable. If
Yobot is normally attached to something else, stop it there first and move the
USB cable across.
