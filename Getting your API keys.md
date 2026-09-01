# Getting Your API Keys

> **¿Prefieres español?** Lee **`Obtener tus llaves API (Espanol).md`**.

This guide walks you through getting the keys Yobot needs. **One is required
and one is optional**, so read the next section before you sign up for
anything.

**You do NOT need to be a programmer to do this.** Just follow the steps.

---

## What Are API Keys and Why Do You Need Them?

An API key is like a password that lets Yobot talk to an outside service.

**You need one: Microsoft Azure.** That is the voice — speaking out loud, and
hearing you through the microphone. Without it Yobot still moves, but in
silence, and the chess show has nothing to speak with either. **Part 1** below.

**The second one is optional and can wait.** It is the brain: what lets Yobot
hold a conversation with somebody. Nothing else touches it — not the motors,
not the control panel, not chess. And it does not have to be OpenAI; several
companies work, and one of them runs on your own machine for nothing.
**Part 2** below.

Do Part 1 now. Part 2 can be another day, without redoing anything.

> **With no keys at all:** the motor controls, sliders, LED picker and sequence
> builder all still work fine. Keys are only for speech and conversation.

---

## ⚠️ Fair Warning About Azure

Microsoft's Azure website is designed for big corporate IT departments. It is **not** beginner-friendly. It's full of confusing menus, enterprise jargon, and options you'll never need. Don't let it intimidate you — you only need to find two things: a **key** and a **region**. This guide will point you straight to them.

---

## Part 1 — Azure Speech Key *(required — this is the voice)*

### Step 1 — Create a free Azure account

1. Go to [https://azure.microsoft.com/free](https://azure.microsoft.com/free)
2. Click **Start free**
3. Sign in with a Microsoft account (or create one — Outlook, Hotmail, or any Microsoft account works)
4. You'll be asked for a credit card. Azure requires it to verify your identity, but **the free tier will not charge you** unless you manually upgrade. Light hobby use typically stays well under the free limits.

> **Free tier includes:** 5 hours of speech-to-text and 500,000 characters of text-to-speech per month. For a hobby robot, that's essentially unlimited.

---

### Step 2 — Create a Speech resource

This is where Azure gets confusing. Follow these steps exactly.

1. Once logged in, you'll land on the Azure Portal home page at [https://portal.azure.com](https://portal.azure.com)
   - It looks overwhelming. Ignore most of it.

2. In the search bar at the very top of the page, type **Speech** and press Enter

3. In the results, look for **Speech services** (it may say "Cognitive Services" underneath — that's normal). Click it.

4. Click the **+ Create** button (blue button, top left area)

5. You'll see a form. Fill it in:

   | Field | What to enter |
   |-------|--------------|
   | **Subscription** | Leave as-is (your free subscription) |
   | **Resource group** | Click "Create new" and type any name, like `ohbot-keys` |
   | **Region** | Pick the region closest to you (see note below) |
   | **Name** | Type any name, like `ohbot-speech` |
   | **Pricing tier** | Select **Free F0** |

   > **Region matters for speed.** Pick the one geographically closest to where your Pi will be. Common choices: `East US`, `West Europe`, `Australia East`, `Southeast Asia`. **Write down exactly what you pick** — you'll need it later.

6. Click **Review + create**, then click **Create**

7. Wait about 30 seconds while Azure sets it up. Then click **Go to resource**.

---

### Step 3 — Find your key and region

You're now on your Speech resource page. Still confusing-looking — here's where to look:

1. On the left sidebar, look for **Keys and Endpoint** and click it
   - If you don't see it, look for **Resource Management** in the left menu and expand it

2. You'll see two keys: **KEY 1** and **KEY 2**. They're identical — you only need one. Click the copy icon next to **KEY 1**.

3. Paste it somewhere safe (a text file, a note on your phone — anywhere you won't lose it).

4. On that same page, find the **Location/Region** field. It will say something like `eastus` or `westeurope` — all lowercase, no spaces. Copy that too.

**That's your Azure setup done.** You now have:
- ✅ `AZURE_SPEECH_KEY` — the long string of letters and numbers from KEY 1
- ✅ `AZURE_SPEECH_REGION` — the short region code like `eastus`

---

## Part 2 — The brain *(optional — skip it if you only want speech and chess)*

Yobot is not tied to one AI company. All of these speak the same language to
it, so switching between them is a setting, not a rebuild. **Pick one:**

| Company | Where the key comes from | Worth knowing |
|---|---|---|
| **OpenAI** | [platform.openai.com](https://platform.openai.com) → API keys | The default, and what Yobot has always used. Walked through below. |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) → API keys | Claude. |
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Has a free tier. |
| **Groq** | [console.groq.com](https://console.groq.com) → API keys | Runs open models on its own hardware — fast, and very cheap. |
| **Ollama** | nothing to sign up for | Runs on your own computer or network. No account, no bill, and nothing you say leaves the building. |

The steps below are for OpenAI, because it is the most common starting point.
**The other sites work the same way**: make an account, find the API keys page,
create a key, copy it immediately. Then tell Yobot which company you picked —
that is the `LLM_PROVIDER` line in Part 3.

OpenAI's website is much friendlier than Azure.

### Step 1 — Create an OpenAI account

1. Go to [https://platform.openai.com](https://platform.openai.com)
   - Note: this is the **developer platform**, not the regular ChatGPT chat website. Different place.

2. Click **Sign up** and create an account (or log in if you already have one)

---

### Step 2 — Add a payment method

The OpenAI API is **not free**, but it's very cheap for hobby use. A few dollars of credit will last months for a personal robot project.

1. Once logged in, click your account icon (top right) → **Billing**
2. Click **Add payment method** and enter a credit or debit card
3. You can set a **monthly spending limit** — $5 is plenty to start. OpenAI will stop charging you when you hit it.

> **How cheap is it really?** A typical short conversation with GPT-4o-mini costs a fraction of a cent. You'd need to have thousands of conversations to spend even $1.

---

### Step 3 — Create an API key

1. In the left sidebar, click **API keys** (or go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys))

2. Click **+ Create new secret key**

3. Give it a name like `ohbot` (optional but helpful)

4. Click **Create secret key**

5. **Copy the key immediately** — OpenAI only shows it once. If you miss it, you'll have to create a new one.

   The key starts with `sk-` followed by a long string of characters.

**That's OpenAI done.** You now have:
- ✅ `OPENAI_API_KEY` — the `sk-...` string

---

## Part 3 — Put the Keys In

### The easy way — the Settings page

Once Yobot is running, open the Launcher page in a browser and click
**`⚙ Settings & Keys`**. Paste your Azure key there, choose which AI company
the brain uses if you got one, and press the button that tests each key and
tells you whether it actually answers. It writes the same file the hard way
below writes, without a terminal and without hunting for hidden file
extensions.

Anyone on the same WiFi can open the Launcher, so the first time you use
Settings it offers to set a password. Until you set one it stays unlocked, so
a fresh install cannot lock you out of the page you need to set it from.

The rest of this Part is the other way — editing the file by hand. It still
works and it is worth knowing.

### Log into your Pi

You need a terminal connection to your Pi. Pick whichever method fits your situation:

**On a Mac or Linux computer — use SSH:**

Open the Terminal app and type:

```bash
ssh YOUR_USERNAME@YOUR.PI.IP.ADDRESS
```

For example: `ssh pi@192.168.1.42`

To find your Pi's IP address, you can check your router's device list, or if your Pi has a screen attached, run `hostname -I` on it.

**On a Windows computer — use PuTTY:**

1. Download PuTTY (free) from [https://www.putty.org](https://www.putty.org)
2. Open PuTTY
3. In the **Host Name** field, type your Pi's IP address (e.g. `192.168.1.42`)
4. Make sure **Port** is `22` and **Connection type** is `SSH`
5. Click **Open**
6. Log in with your Pi username and password when prompted

Once you're connected, you'll see a command prompt on the Pi. Now create the `.env` file:

```bash
cd ~/Projects/Ohbot
nano .env
```

Type (or paste) the following, replacing the placeholder text with your real
key and region:

```
AZURE_SPEECH_KEY=paste_your_azure_key_here
AZURE_SPEECH_REGION=paste_your_region_here
```

**Those two lines are a complete, working file.** With them Yobot moves,
speaks, and plays chess.

If you did Part 2 and want the conversation as well, add two more lines —
which company, and its key:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=paste_your_openai_key_here
```

Use whichever you picked: `anthropic` with `ANTHROPIC_API_KEY`, `gemini` with
`GEMINI_API_KEY`, `groq` with `GROQ_API_KEY`, or `ollama`, which needs no key
at all. Leave `LLM_PROVIDER` out entirely and Yobot assumes OpenAI, exactly as
it always did.

Save and exit nano: press **Ctrl+X**, then **Y**, then **Enter**.

---

## Verify It's Working

After saving the `.env` file, start the GUI server:

```bash
cd ~/Projects/Ohbot
source venv/bin/activate
python3 gui_server.py
```

Open the GUI in your browser. If the keys are correct:
- The **Text-to-Speech** box should work — type something and click Speak
- The **AI Chat** panel should respond when you send a message, *if* you set
  up a brain in Part 2. With no brain key, the rest still works and only the
  chat panel stays quiet — that is not a fault.

Quicker still: the **`⚙ Settings & Keys`** page has a test button for each
key, and it says what is wrong rather than just failing.

If something isn't working, double-check:
1. The `.env` file is in the right folder (`~/Projects/Ohbot/.env`)
2. There are no extra spaces around the `=` sign
3. The region code is lowercase with no spaces (e.g., `eastus` not `East US`)

---

## Keep Your Keys Safe

- **Never share your `.env` file** — anyone with your keys can use your accounts and run up charges
- **Never paste your keys into a chat, email, or document**
- The `.gitignore` file in this project already protects the `.env` file from being accidentally uploaded to GitHub
- If you think a key was exposed, go back to Azure or OpenAI and delete it, then create a new one

---

## Quick Reference

| What you need | Where to get it | Cost |
|---|---|---|
| `AZURE_SPEECH_KEY` | portal.azure.com → your Speech resource → Keys and Endpoint | Free tier available (5hrs STT + 500K chars TTS/month) |
| `AZURE_SPEECH_REGION` | Same page — the Location/Region field | — |
| `LLM_PROVIDER` | Not a key — the name of the company you picked: `openai`, `anthropic`, `gemini`, `groq` or `ollama` | — |
| the brain's key | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` or `GROQ_API_KEY`, from that company's own site | Pay-as-you-go, roughly $1–3/month for hobby use. Ollama needs no key and costs nothing. |

**Only the two Azure rows are required.** Everything below them is the
conversation, and the conversation is optional.
