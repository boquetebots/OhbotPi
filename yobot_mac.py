#!/usr/bin/env python3
"""
Yobot on macOS — Launcher
Version: 1.0.0

The Mac front door for the Yobot project (Panama). Uses the same shared
yobot_core library as the Raspberry Pi — nothing here is Mac-only except
this launcher's help text.

Three ways to run it:

  python3 yobot_mac.py test
      Hardware smoke test — no internet or API keys needed.
      Moves the head, blinks, cycles the eye LEDs, resets.
      Run this FIRST after plugging Yobot into the Mac.

  python3 yobot_mac.py say "Hello there!"
      Speaks through Azure with full lip sync — tests audio output,
      the API keys, and lip sync. Needs internet + .env keys.

  python3 yobot_mac.py
      The full conversation bot. Starts the brain server
      (ohbotchat_server.py) automatically, then listens and chats.
      Wake a sleeping Yobot by pressing Enter.

Audio: uses the Mac's current default microphone and speaker
(whatever is selected in System Settings → Sound).

Remember: only one computer can run Yobot at a time. Stop the Pi's
services and plug the USB cable into the Mac first — see SETUP_MacOS.md.
"""

import os
import sys
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY CHECK — fail with friendly instructions, not a crash
# ─────────────────────────────────────────────────────────────────────────────

def check_dependencies(need_azure=False, need_chat=False):
    missing = []

    def probe(module, pip_name):
        try:
            __import__(module)
        except ImportError:
            missing.append(pip_name)

    probe("serial", "pyserial")
    probe("lxml", "lxml")
    if need_azure or need_chat:
        probe("azure.cognitiveservices.speech", "azure-cognitiveservices-speech")
    if need_chat:
        probe("httpx", "httpx")
        probe("flask", "flask")
        probe("openai", "openai")

    if missing:
        print("❌ Some Python packages are missing.")
        print("   If you haven't made Yobot's venv yet, paste these two lines:\n")
        print("   python3 -m venv ~/yobot-venv")
        print(f"   ~/yobot-venv/bin/pip install {' '.join(missing)}\n")
        print("   Then always run Yobot with:  ~/yobot-venv/bin/python3 yobot_mac.py")
        print("   (Full guide: SETUP_MacOS.md in the OhbotPi2 folder)")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# MODE 1: HARDWARE TEST (no internet needed)
# ─────────────────────────────────────────────────────────────────────────────

def run_hardware_test():
    check_dependencies()
    import yobot_core as yobot

    print("=" * 60)
    print(f"  Yobot Hardware Test  —  {yobot.PLATFORM}")
    print("=" * 60)

    if not yobot.init():
        print("\nTroubleshooting:")
        print("  1. Is the USB cable plugged into THIS Mac (not the Pi)?")
        print("  2. Is Yobot's power supply on?")
        print("  3. Unplug the USB cable, wait 5 seconds, plug it back in.")
        sys.exit(1)

    print("\n✅ Connected! Running movement test...\n")

    print("  Eyes green...")
    yobot.baseColour(0, 10, 0)
    yobot.wait(1)

    print("  Head turn left / right...")
    yobot.move(yobot.HEADTURN, 7, 4)
    yobot.wait(1)
    yobot.move(yobot.HEADTURN, 3, 4)
    yobot.wait(1)
    yobot.move(yobot.HEADTURN, 5, 4)
    yobot.wait(1)

    print("  Head nod...")
    yobot.move(yobot.HEADNOD, 7, 4)
    yobot.wait(0.8)
    yobot.move(yobot.HEADNOD, 3, 4)
    yobot.wait(0.8)
    yobot.move(yobot.HEADNOD, 5, 4)
    yobot.wait(1)

    print("  Blink...")
    yobot.move(yobot.LIDBLINK, 0, 10)
    yobot.wait(0.3)
    yobot.move(yobot.LIDBLINK, 10, 10)
    yobot.wait(1)

    print("  Mouth open / close...")
    yobot.move(yobot.TOPLIP, 7, 5)
    yobot.move(yobot.BOTTOMLIP, 7, 5)
    yobot.wait(1)
    yobot.move(yobot.TOPLIP, 5, 5, avoid=False)
    yobot.move(yobot.BOTTOMLIP, 5, 5, avoid=False)
    yobot.wait(1)

    print("  Eye colors: red... blue... off")
    yobot.baseColour(10, 0, 0)
    yobot.wait(0.7)
    yobot.baseColour(0, 0, 10)
    yobot.wait(0.7)

    print("  Reset to rest position...")
    yobot.reset()
    yobot.close()

    print("\n✅ Hardware test complete! If the head moved and the eyes")
    print("   changed color, Yobot is working on this Mac.")
    print("   Next step:  python3 yobot_mac.py say \"Hello from my Mac!\"")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 2: SPEECH TEST (needs internet + .env keys)
# ─────────────────────────────────────────────────────────────────────────────

def run_say(text):
    check_dependencies(need_azure=True)
    import asyncio
    import yobot_core as yobot

    if not os.environ.get("AZURE_SPEECH_KEY"):
        print("❌ AZURE_SPEECH_KEY not found.")
        print("   Make sure the .env file is in the same folder as this script.")
        sys.exit(1)

    from ohbot_azure import AzureSpeechManager, AsyncOhbotController

    async def _say():
        print("Connecting to Yobot...")
        if not yobot.init():
            print("(no robot found — will speak without moving)")

        azure = AzureSpeechManager()
        controller = AsyncOhbotController(azure)
        await controller.start()
        try:
            await controller.set_eye_color(0, 10, 5)
            await controller.say(text)
            await controller.set_eye_color(0, 0, 0)
        finally:
            await controller.stop()

    asyncio.run(_say())
    print("\n✅ If you heard the voice from the Mac's speaker and saw the")
    print("   mouth move, speech is fully working.")
    print("   Next step:  python3 yobot_mac.py   (the full conversation bot)")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 3: FULL CONVERSATION BOT
# ─────────────────────────────────────────────────────────────────────────────

def run_full_bot():
    check_dependencies(need_azure=True, need_chat=True)
    import asyncio
    import yobot_core  # noqa: F401 — loads the .env keys

    import httpx

    # Start the brain server (handles OpenAI) as a background process,
    # unless one is already running (e.g. started by hand).
    server_url = os.environ.get("OHBOT_SERVER_URL", "http://localhost:5002")
    server_proc = None

    def server_alive():
        try:
            r = httpx.get(f"{server_url}/health", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    if server_alive():
        print("✅ Brain server already running")
    else:
        print("Starting brain server (ohbotchat_server.py)...")
        server_proc = subprocess.Popen(
            [sys.executable, os.path.join(SCRIPT_DIR, "ohbotchat_server.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):          # wait up to ~15 seconds
            if server_alive():
                print("✅ Brain server is up")
                break
            time.sleep(0.5)
        else:
            print("❌ Brain server didn't start. Try running it by hand to")
            print("   see the error:  python3 ohbotchat_server.py")
            if server_proc:
                server_proc.terminate()
            sys.exit(1)

    # Run the conversation bot (same code as the Pi)
    import ohbot_chat
    try:
        asyncio.run(ohbot_chat.main())
    except KeyboardInterrupt:
        pass
    finally:
        if server_proc:
            print("Stopping brain server...")
            server_proc.terminate()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_hardware_test()
    elif len(sys.argv) > 1 and sys.argv[1] == "say":
        if len(sys.argv) < 3:
            print('Usage:  python3 yobot_mac.py say "Something to say"')
            sys.exit(1)
        run_say(sys.argv[2])
    elif len(sys.argv) > 1:
        print(f"Unknown option: {sys.argv[1]}")
        print(__doc__)
        sys.exit(1)
    else:
        run_full_bot()
