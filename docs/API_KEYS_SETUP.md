# Getting Your API Keys — Azure Speech & OpenAI

This guide walks you through getting the two API keys Ohbot needs for speech and AI chat.

**You do NOT need to be a programmer to do this.** Just follow the steps.

---

## What Are API Keys and Why Do You Need Them?

An API key is like a password that lets Ohbot talk to an outside service.

- **Azure Speech key** — lets Ohbot speak out loud (text-to-speech) and understand what you say (microphone input)
- **OpenAI key** — lets Ohbot have AI-powered conversations using ChatGPT

Both services have free tiers or very low cost for personal/hobby use.

> **Without these keys:** The motor controls, sliders, LED picker, and sequence builder all still work fine. You only need the keys if you want speech or AI chat.

---

## ⚠️ Fair Warning About Azure

Microsoft's Azure website is designed for big corporate IT departments. It is **not** beginner-friendly. It's full of confusing menus, enterprise jargon, and options you'll never need. Don't let it intimidate you — you only need to find two things: a **key** and a **region**. This guide will point you straight to them.

---

## Part 1 — Azure Speech Key

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

## Part 2 — OpenAI Key

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

## Part 3 — Put the Keys on Your Pi

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

Type (or paste) the following, replacing the placeholder text with your actual keys:

```
AZURE_SPEECH_KEY=paste_your_azure_key_here
AZURE_SPEECH_REGION=paste_your_region_here
OPENAI_API_KEY=paste_your_openai_key_here
```

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
- The **AI Chat** panel should respond when you send a message

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
| `OPENAI_API_KEY` | platform.openai.com → API keys | Pay-as-you-go, ~$1–3/month for hobby use |
