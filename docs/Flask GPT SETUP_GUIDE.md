# Ohbot OpenAI Conversation Setup

## 🎯 What This Does
- Ohbot asks: "Can I help you with something?"
- Listens to you (Azure STT)
- Sends your question to OpenAI GPT-4o-mini via Flask server
- Speaks the response (Azure TTS with lip sync)
- Maintains conversation context for 5 exchanges
- Clear error messages for all failure cases

## 📋 Setup Instructions

### 1. Install Requirements
```bash
cd ~/ohbot_project
pip install -r requirements_conversation.txt
```

### 2. Set Environment Variables

Add to your `~/.bashrc` (if not already there):
```bash
export AZURE_SPEECH_KEY="your-azure-key"
export AZURE_SPEECH_REGION="eastus"  # or your region
export OPENAI_API_KEY="your-openai-key"
```

Then reload:
```bash
source ~/.bashrc
```

### 3. Verify Environment Variables
```bash
echo $AZURE_SPEECH_KEY
echo $AZURE_SPEECH_REGION
echo $OPENAI_API_KEY
```

## 🚀 Running the System

### Step 1: Start Flask Server (Terminal 1)
```bash
python3 ohbotchat_server.py
```

You should see:
```
🤖 Ohbot Flask Server Starting...
OpenAI API Key: ✅ Set
Model: gpt-4o-mini
Max conversation length: 5 exchanges
🌐 Server starting on http://localhost:5000
```

### Step 2: Run Ohbot Conversation (Terminal 2)
```bash
python3 ohbot_chat.py
```

The conversation will:
1. ✅ Connect to Ohbot hardware
2. ✅ Check Flask server is running
3. 🗣️ Say "Hello! Can I help you with something?"
4. 🎤 Listen for your input
5. 📡 Send to OpenAI via Flask
6. 🗣️ Speak the response
7. Repeat for 5 exchanges

## 🎨 LED Color Indicators

- **Green** (0, 10, 0) - Ready/waiting
- **Orange** (10, 5, 0) - Listening
- **Blue** (5, 5, 10) - Thinking (calling OpenAI)
- **Cyan** (0, 10, 5) - Speaking
- **Red** (10, 0, 0) - Error
- **Purple** (10, 0, 10) - Done

## ⚠️ Error Messages

The system gives clear spoken feedback:

| Error | Ohbot Says |
|-------|------------|
| No speech detected | "No speech detected. Please try again." |
| Network failure | "There are network issues. Please check your connection." |
| OpenAI API failure | "OpenAI API failed. Please try again later." |

## 🔧 Troubleshooting

### "Flask server not reachable"
```bash
# In separate terminal:
python3 ohbotchat_server.py
```

### "Ohbot not found"
```bash
# Check USB connection
ls /dev/ttyACM* /dev/ttyUSB*

# Replug USB cable
# Try different USB port
```

### "AZURE_SPEECH_KEY not set"
```bash
export AZURE_SPEECH_KEY="your-key"
source ~/.bashrc
```

### "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="your-key"
source ~/.bashrc
```

## 📁 Files Created

```
ohbotchat_server.py              # Flask server (OpenAI integration)
ohbot_chat.py        # Main conversation script
requirements_conversation.txt # Python dependencies
SETUP_GUIDE.md              # This file
```

## 🧪 Test Flask Server Independently

```bash
# Start server
python3 ohbotchat_server.py

# In another terminal, test with curl:
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# Should return:
# {"response":"I'm doing great, thanks for asking!","success":true}
```

## 🎯 Customization

### Change GPT Model
Edit `ohbotchat_server.py`, line 77:
```python
model="gpt-4o-mini",  # Change to "gpt-4o" for more capable model
```

### Change Voice
Edit `ohbot_chat.py`, line 40:
```python
self.speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"  # Female
# or
self.speech_config.speech_synthesis_voice_name = "en-US-GuyNeural"  # Male
```

### Change Conversation Length
Edit `ohbot_chat.py`, line 263:
```python
for exchange_num in range(1, 11):  # Change to 11 for 10 exchanges
```

Also edit `ohbotchat_server.py`, line 19:
```python
conversation_history = deque(maxlen=20)  # 20 messages = 10 exchanges
```

### Change System Prompt (Personality)
Edit `ohbotchat_server.py`, lines 22-24:
```python
SYSTEM_PROMPT = """You are Ohbot, a sarcastic robot comedian..."""
```

## 🔄 Reset Conversation Memory

```bash
curl -X POST http://localhost:5000/reset
```

Or restart the Flask server.

## 💡 Tips

1. **Speak clearly** - Azure STT works best with clear speech
2. **Wait for LED** - Orange = listening, speak when you see it
3. **Quiet environment** - Reduces false triggers
4. **One question at a time** - Better STT accuracy
5. **USB power** - Use powered hub if motors stutter

## 📊 Server Endpoints

- `GET /` - Status page (view in browser)
- `POST /chat` - Send message to OpenAI
- `POST /reset` - Clear conversation history
- `GET /health` - Health check

## 🎉 Success Criteria

You know it's working when:
- ✅ Flask server starts without errors
- ✅ Ohbot says "Hello! Can I help you with something?"
- ✅ Eyes turn orange when listening
- ✅ Eyes turn blue when thinking
- ✅ Ohbot speaks GPT's response with lip sync
- ✅ Conversation continues for 5 exchanges

Enjoy your conversational Ohbot! 🤖
