#!/usr/bin/env python3
"""
Ohbot for Raspberry Pi - Streamlined, Async-First
Version: 5.0.0-pi
Platform: Linux/Raspberry Pi only
Features: Piper TTS, Async audio, GRB LED support
"""

import asyncio
import serial
import serial.tools.list_ports
import os
import subprocess
import tempfile
from pathlib import Path
from lxml import etree
from concurrent.futures import ThreadPoolExecutor

# ============================================================================
# CONSTANTS
# ============================================================================

VERSION = "5.0.0-pi"

# Motor constants
HEADNOD = 0
HEADTURN = 1
EYETURN = 2
LIDBLINK = 3
TOPLIP = 4
BOTTOMLIP = 5
EYETILT = 6
HEADROLL = 7

# ============================================================================
# GLOBALS
# ============================================================================

# Serial connection
ser = None
connected = False
port = ""

# Motor state
motorPos = [5, 5, 5, 5, 5, 5, 5, 5]
motorMins = [0, 0, 0, 0, 0, 0, 0, 0]
motorMaxs = [0, 0, 0, 0, 0, 0, 0, 0]
motorRev = [False, False, False, False, False, False, False, False]
restPos = [5, 5, 5, 5, 5, 5, 5, 5]
isAttached = [False, False, False, False, False, False, False, False]

# Eye state  
eyeShapes = []
lastfexl = 5
lastfexr = 5
lastfeyl = 5
lastfeyr = 5

# Paths
ohbotDataDir = 'ohbotData'
motorDefFile = 'ohbotData/MotorDefinitionsv21.omd'
eyeShapeFile = 'ohbotData/ohbot.obe'

# Debug
debug = False

# ============================================================================
# PIPER TTS CLASS
# ===========================================================================

class PiperTTS:
    """Lightweight Piper TTS wrapper"""
    
    def __init__(self):
        self.piper_path = None
        self.voice_path = None
        self.available_voices = []
        self._find_piper()
    
    def _find_piper(self):
        """Find piper executable"""
        # Check venv first (where pip installs it)
        if hasattr(os.sys, 'prefix'):
            venv_bin = Path(os.sys.prefix) / 'bin' / 'piper'
            if venv_bin.exists():
                self.piper_path = str(venv_bin)
                if debug:
                    print(f"Found piper in venv: {self.piper_path}")
        
        # Fallback to PATH
        if not self.piper_path:
            result = subprocess.run(['which', 'piper'], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                self.piper_path = result.stdout.strip()
        
        if self.piper_path:
            self._find_voices()
        elif debug:
            print("Piper executable not found")
    
    def _find_voices(self):
        """Find voice models"""
        # Get the directory where ohbot_pi.py is located
        script_dir = Path(__file__).parent.resolve()
        
        possible_dirs = [
            script_dir / 'data' / 'piper_models',  # Relative to script
            Path.home() / 'ohbot_project' / 'data' / 'piper_models',  # Absolute path
            Path.home() / 'piper_models',
            Path.home() / '.local' / 'share' / 'piper-tts',
        ]
        
        for voice_dir in possible_dirs:
            if voice_dir.exists():
                self.available_voices = [v for v in voice_dir.glob('**/*.onnx') 
                                        if 'tashkeel' not in str(v)]
                if self.available_voices:
                    self.voice_path = str(self.available_voices[0])
                    if debug:
                        print(f"Found {len(self.available_voices)} voice(s) in {voice_dir}")
                    break
        
        if not self.available_voices and debug:
            print("No voice models found")
    
    def is_available(self):
        """Check if piper and voices are available"""
        return self.piper_path is not None and self.voice_path is not None
    
    def set_voice(self, voice_name):
        """Set voice by name"""
        for v in self.available_voices:
            if voice_name in str(v):
                self.voice_path = str(v)
                return True
        return False
    
    def generate_speech(self, text, output_file):
        """Generate speech file"""
        if not self.piper_path:
            raise RuntimeError("Piper executable not found")
        if not self.voice_path:
            raise RuntimeError("No voice available")
        
        cmd = [self.piper_path, '--model', self.voice_path, 
               '--output_file', output_file]
        
        result = subprocess.run(cmd, input=text, text=True,
                               capture_output=True, timeout=10)
        
        if result.returncode != 0:
            raise RuntimeError(f"Piper failed: {result.stderr}")

# Global TTS instance
piper = PiperTTS()


# ============================================================================
# ASYNC CONTROLLER
# ============================================================================

class OhbotController:
    """Async Ohbot controller"""
    
    def __init__(self):
        self.io_executor = ThreadPoolExecutor(max_workers=2)
        self.is_speaking = False
        self.audio_is_playing = False
    
    async def say(self, text, lip_sync=True):
        """Speak with optional lip sync"""
        if not text or text.isspace():
            return
        
        self.is_speaking = True
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file = f.name
            
            # Generate audio in thread
            await asyncio.get_event_loop().run_in_executor(
                self.io_executor,
                piper.generate_speech,
                text,
                temp_file
            )
            
            # Analyze for lip sync if enabled
            lip_data = None
            if lip_sync:
                lip_data = await asyncio.get_event_loop().run_in_executor(
                    self.io_executor,
                    self._analyze_audio_for_lips,
                    temp_file
                )
            
            # Start lip sync task if we have data
            lip_task = None
            if lip_sync and lip_data:
                lip_task = asyncio.create_task(
                    self._animate_lips(lip_data)
                )
            
            # Play audio async
            await self._play_audio_async(temp_file)
            
            # Wait for lip sync to finish
            if lip_task:
                await lip_task
            
            os.unlink(temp_file)
            
        finally:
            self.is_speaking = False
            # Reset lips to neutral (avoid=False so they can close after opening)
            if lip_sync:
                _move(TOPLIP, 5, 10, avoid=False)
                _move(BOTTOMLIP, 5, 10, avoid=False)
    
    def _analyze_audio_for_lips(self, audio_file):
        """Analyze audio waveform for lip movement data"""
        import wave
        
        try:
            waveFile = wave.open(audio_file, 'r')
            
            framerate = waveFile.getframerate()
            channels = waveFile.getnchannels()
            bytespersample = waveFile.getsampwidth()
            length = waveFile.getnframes()
            
            # Samples per viseme calculation (20 per second gives smooth movement)
            VISEMES_PER_SEC = 20
            chunk = int(framerate / VISEMES_PER_SEC)
            
            volumes = []
            times = []
            ms = 0
            
            # Read audio in chunks and calculate volume
            for i in range(0, length - chunk, chunk):
                vol = 0
                buffer = waveFile.readframes(chunk)
                bytesread = chunk * channels * bytespersample
                
                index = 0
                for sample in range(0, int(bytesread / (channels * bytespersample))):
                    # Read 16-bit sample (little endian)
                    vol += buffer[index] + (buffer[index + 1] << 8)
                    index += bytespersample
                    
                    # If stereo, add second channel
                    if channels > 1:
                        vol += buffer[index] + (buffer[index + 1] << 8)
                        index += bytespersample
                
                volumes.append(float(vol))
                times.append(ms / 1000.0)
                ms += (1000 / VISEMES_PER_SEC)
            
            waveFile.close()
            
            # Normalize volumes to 0-10 range
            if volumes:
                max_vol = max(volumes)
                if max_vol > 0:
                    volumes = [(v / max_vol) * 10 for v in volumes]
            
            return {'volumes': volumes, 'times': times}
            
        except Exception as e:
            if debug:
                print(f"Audio analysis failed: {e}")
            return None
    
    async def _animate_lips(self, lip_data):
        """Animate lips based on volume data"""
        if not lip_data or not lip_data['volumes']:
            return
        
        volumes = lip_data['volumes']
        times = lip_data['times']
        
        start_time = asyncio.get_event_loop().time()
        current_idx = 0
        
        while current_idx < len(times):
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # Find current volume based on time
            while current_idx < len(times) and times[current_idx] < elapsed:
                current_idx += 1
            
            if current_idx >= len(volumes):
                break
            
            vol = volumes[current_idx]
            
            # Map volume to lip positions
            # Top lip: 5 (closed) to 7-8 (open)
            # Bottom lip: 5 (closed) to 7-8 (open)
            # Map volume to lip positions with threshold and non-linear response
            if vol < 3.0:  # Ignore quiet sounds below threshold
                top_pos = 5
                bottom_pos = 5
            else:
    # Square the volume for exponential response (makes loud sounds more dramatic)
                vol_scaled = (vol / 10) ** 2
                top_pos = 5 + vol_scaled * 3.5      # Top lip
                bottom_pos = 5 + vol_scaled * 4.5   # Bottom lip moves more
            # Move bottom lip first so the avoidance clamp in _move()
            # sees the correct bottom position when evaluating the top lip.
            _move(BOTTOMLIP, int(bottom_pos), 10)
            _move(TOPLIP, int(top_pos), 10)
            
            # Small delay to prevent overwhelming serial
            await asyncio.sleep(0.02)
        
        # Reset lips (avoid=False so they can close after opening)
        _move(TOPLIP, 5, 10, avoid=False)
        _move(BOTTOMLIP, 5, 10, avoid=False)
    
    async def _play_audio_async(self, audio_file):
        """Truly async audio playback"""
        process = await asyncio.create_subprocess_exec(
            'aplay', '-D', 'plug:default', audio_file,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        
        self.audio_is_playing = True
        await process.wait()
        self.audio_is_playing = False
    
    async def move(self, motor, position, speed=5):
        """Async motor move"""
        _move(motor, position, speed)
        await asyncio.sleep(0.01)

# Global controller
controller = OhbotController()
# ============================================================================
# INITIALIZATION
# ============================================================================

def init(portName=None):
    """Initialize Ohbot"""
    global port, ser, connected
    
    # Create data directory
    os.makedirs(ohbotDataDir, exist_ok=True)
    
    # Load motor definitions
    _loadMotorDefs()
    
    # Load eye shapes
    _loadEyeShapes()
    
    # Find serial port
    ports = list(serial.tools.list_ports.comports())
    
    if portName:
        if _checkPort([portName]):
            port = portName
            connected = True
    else:
        for p in ports:
            if "usb" in p[0].lower() or "acm" in p[0].lower():
                if _checkPort(p):
                    port = p[0]
                    connected = True
                    print(f"Ohbot found on port: {port}")
                    break
    
    if not connected:
        print("Ohbot not found - running without hardware")
        return False
    
    # Open serial port
    try:
        ser = serial.Serial(port, 19200)
        ser.timeout = None
        ser.write_timeout = None
        return True
    except:
        print(f"Could not connect to {port}")
        return False

def _checkPort(p):
    """Check if port has Ohbot"""
    try:
        test_ser = serial.Serial(p[0], 19200, timeout=0.5)
        test_ser.write("v\n".encode('latin-1'))
        line = test_ser.readline()
        test_ser.close()
        return b"v1" in line or b"v2" in line
    except:
        return False

# ============================================================================
# MOTOR CONTROL
# ============================================================================

def _get_api_pos(m):
    """Return the last-commanded API position (0-10) for motor m.
    motorPos stores the post-reversal value, so we undo that here."""
    return (10 - motorPos[m]) if motorRev[m] else motorPos[m]


def _move(m, pos, spd=5, avoid=True):
    """Move a motor (internal).
    avoid=True  → lip crossing protection active (normal user/slider moves).
    avoid=False → bypass protection (lip sync resets, reset() closing moves).
    """
    global motorPos

    pos = max(0, min(10, pos))
    spd = max(0, min(10, spd))

    # ── Lip avoidance ──────────────────────────────────────────────────────
    # Rule: TopLip position + BottomLip position must always add up to at
    # least 10. Equivalently, each lip's minimum allowed position is
    # (10 - the other lip's current position).
    #
    # This means opening one lip further always FREES UP room for the other
    # lip to move lower — it never traps the other lip the way a simple
    # "can't go below the other's raw position" rule would (that older rule
    # could ratchet both lips up to the same value and then deadlock, since
    # neither could move down without the other moving first).
    #
    # avoid=False is used for programmatic resets (lip sync end, Reset button)
    # so the mouth can close after opening without this check getting in the way.
    if avoid:
        if m == TOPLIP:
            bot_api = _get_api_pos(BOTTOMLIP)
            pos = max(pos, 10 - bot_api)   # top can't go below (10 - bottom)
        elif m == BOTTOMLIP:
            top_api = _get_api_pos(TOPLIP)
            pos = max(pos, 10 - top_api)   # bottom can't go below (10 - top)
    # ───────────────────────────────────────────────────────────────────────

    # Reverse if needed
    if motorRev[m]:
        pos = 10 - pos

    # Attach motor
    if not isAttached[m]:
        _attach(m)

    # Convert to degrees
    absPos = int(_getPos(m, pos))
    spd = int((250 / 10) * spd)

    # Send command
    msg = f"m0{m},{absPos},{spd}\n"
    _serwrite(msg)

    motorPos[m] = pos

def move(m, pos, spd=5, avoid=True):
    """Move motor (sync version for compatibility)"""
    _move(m, pos, spd, avoid)

def _attach(m):
    """Attach motor"""
    global isAttached
    msg = f"a0{m}\n"
    _serwrite(msg)
    isAttached[m] = True

def detach(m):
    """Detach motor"""
    global isAttached
    msg = f"d0{m}\n"
    _serwrite(msg)
    isAttached[m] = False

def _getPos(m, pos):
    """Calculate motor position"""
    mRange = motorMaxs[m] - motorMins[m]
    return (mRange / 10) * pos + motorMins[m]

def reset():
    """Reset to rest position"""
    baseColour(0, 0, 0)
    for i, pos in enumerate(restPos):
        if i in (TOPLIP, BOTTOMLIP):
            _move(i, pos, avoid=False)   # bypass avoidance so lips can close
        else:
            move(i, pos)
    wait(0.5)

def close():
    """Detach all motors"""
    for i in range(8):
        detach(i)

# ============================================================================
# LED CONTROL
# ============================================================================

def baseColour(r, g, b):
    """Set base LED color (auto-swaps R/G for Pi)"""
    r = max(0, min(10, r))
    g = max(0, min(10, g))
    b = max(0, min(10, b))
    
    # Scale to 0-255
    r = int((255 / 10) * r)
    g = int((255 / 10) * g)
    b = int((255 / 10) * b)
    
    # Swap R and G for Pi GRB LEDs
    msg1 = f"l00,{g},{r},{b}\n"
    msg2 = f"l01,{g},{r},{b}\n"
    
    _serwrite(msg1)
    _serwrite(msg2)

# Aliases
eyeColour = baseColour
setEyeColour = baseColour
setBaseColour = baseColour
setBaseColor = baseColour

# ============================================================================
# EYE SHAPES
# ============================================================================

class EyeShape:
    def __init__(self, name, hexString, autoMirror):
        self.name = name
        self.hexString = hexString
        self.autoMirror = autoMirror

def _loadEyeShapes():
    """Load eye shapes from file"""
    global eyeShapes
    
    if not os.path.exists(eyeShapeFile):
        return
    
    eyeShapes = []
    tree = etree.parse(eyeShapeFile)
    
    for element in tree.iter():
        if element.tag == "Name":
            eyeShapes.append(EyeShape(element.text, "", True))
        elif element.tag == "Hex" and eyeShapes:
            eyeShapes[-1].hexString = element.text
        elif element.tag == "AutoMirror" and eyeShapes:
            eyeShapes[-1].autoMirror = (element.text == "true")

def setEyeShape(shapeNameRight, shapeNameLeft=''):
    """Set eye shape"""
    if not shapeNameLeft:
        shapeNameLeft = shapeNameRight
    
    rightHex = None
    leftHex = None
    autoMirror = True
    
    for shape in eyeShapes:
        if shape.name.upper() == shapeNameRight.upper():
            rightHex = shape.hexString
        if shape.name.upper() == shapeNameLeft.upper():
            leftHex = shape.hexString
            autoMirror = shape.autoMirror
    
    if not leftHex:
        print(f"Eye shape '{shapeNameLeft}' not found")
        return
    
    if connected:
        _setEyes(rightHex or leftHex, leftHex, autoMirror)

def _setEyes(rightDef, leftDef, autoMirror):
    """Set eyes via serial"""
    for i in range(5):
        msg = f"FB,{i},{_eyeShapeBytes(rightDef, leftDef, i, autoMirror)}\n"
        _serwrite(msg)
    # Pupil
    msg = f"FB,8,{_eyeShapeBytes(rightDef, leftDef, 5, autoMirror)}\n"
    _serwrite(msg)

def _eyeShapeBytes(defR, defL, setNo, autoMirror):
    """Convert eye shape to bytes"""
    result = []
    for x in range(9):
        offset = setNo * 18 + x * 2
        left = defL[offset:offset + 2] if autoMirror else _reverseBits(defL[offset:offset + 2])
        right = _reverseBits(defR[offset:offset + 2])
        result.append(left)
        result.append(right)
    return ",".join(result)

def _reverseBits(hex_str):
    """Reverse bits in hex string"""
    x = int(hex_str, 16)
    r = 0
    for i in range(8):
        if x & (1 << (7 - i)):
            r |= (1 << i)
    return f"{r:02X}"

# ============================================================================
# MOTOR DEFINITIONS
# ============================================================================

def _loadMotorDefs():
    """Load motor definitions"""
    global motorMins, motorMaxs, motorRev, restPos
    
    if not os.path.exists(motorDefFile):
        # Use defaults
        return
    
    tree = etree.parse(motorDefFile)
    for child in tree.getroot():
        idx = int(child.get("Motor"))
        motorMins[idx] = int(int(child.get("Min")) / 1000 * 180)
        motorMaxs[idx] = int(int(child.get("Max")) / 1000 * 180)
        restPos[idx] = int(child.get("RestPosition"))
        motorPos[idx] = restPos[idx]
        motorRev[idx] = (child.get("Reverse") == "True")

# ============================================================================
# SERIAL COMMUNICATION
# ============================================================================

def _serwrite(msg):
    """Write to serial port"""
    if debug:
        print(f"Serial: {msg.strip()}")
    
    if connected and ser:
        try:
            ser.write(msg.encode('latin-1'))
        except:
            pass

# ============================================================================
# UTILITIES
# ============================================================================

def wait(seconds):
    """Wait (blocking)"""
    import time
    time.sleep(seconds)

async def async_wait(seconds):
    """Wait (async)"""
    await asyncio.sleep(seconds)

def getVersion():
    """Get library version"""
    return VERSION

# ============================================================================
# SIMPLE TEST
# ============================================================================

async def test():
    """Simple test"""
    print(f"Ohbot Pi Library v{VERSION}")
    print("="*60)
    
    if not init():
        print("No hardware found - exiting")
        return
    
    if piper.is_available():
        print(f"Piper TTS: Available ({len(piper.available_voices)} voices)")
        piper.set_voice("lessac")
    else:
        print("Piper TTS: Not available")
        return
    
    # Test movements
    print("\nTesting...")
    
    baseColour(5, 5, 0)
    
    speech = asyncio.create_task(controller.say("Hello! This is a test of Ohbot on Raspberry Pi!"))
    
    # Wait for audio to start
    while not controller.audio_is_playing:
        await asyncio.sleep(0.01)
    
    # Move during speech
    for _ in range(3):
        await controller.move(HEADTURN, 7, 3)
        await asyncio.sleep(0.5)
        await controller.move(HEADTURN, 3, 3)
        await asyncio.sleep(0.5)
    
    await controller.move(HEADTURN, 5, 3)
    await speech
    
    baseColour(0, 10, 0)
    await controller.say("Test complete!")
    
    baseColour(0, 0, 0)
    reset()
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(test())
