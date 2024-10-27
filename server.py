import os
import json
from dotenv import load_dotenv
import base64
import asyncio
import websockets
import pyaudio
import wave
import webrtcvad
import logging

# ... existing imports and configuration ...

load_dotenv()
# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 5050))
RECOMMENDATION_SUBJECT = "coffee shops"
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to give recommendations "
    f"that the user will love. The user is typically on the road looking for the best {RECOMMENDATION_SUBJECT}."
    "Be open for conversations about coffee as well as discussing where my destination is to help with recommendations."
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created'
]
SHOW_TIMING_MATH = False

# Add these constants
VAD_MODE = 2  # Aggressiveness mode (0-3)
PADDING_DURATION_MS = 300  # ms of padding to add to each audio segment
SILENCE_DURATION = 1  # seconds of silence to consider speech ended
SILENCE_DURATION = 0.5  # Reduce silence duration from 1 second to 0.5 seconds
SPEECH_THRESHOLD = 3  # New constant: number of consecutive speech chunks to consider as actual speech


# Add these constants at the beginning of your file, with the other constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 480

async def capture_audio():
    """Capture audio from microphone and yield chunks with VAD."""
    p = pyaudio.PyAudio()
    vad = webrtcvad.Vad(VAD_MODE)
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    print("Listening... (Speech will be automatically detected)")
    try:
        num_silent_chunks = 0
        num_speech_chunks = 0
        speech_detected = False
        buffer = b''

        while True:
            chunk = stream.read(CHUNK)
            is_speech = vad.is_speech(chunk, RATE)

            if is_speech:
                num_speech_chunks += 1
                if num_speech_chunks >= SPEECH_THRESHOLD:
                    if not speech_detected:
                        print("Speech detected, capturing...")
                    speech_detected = True
                    num_silent_chunks = 0
                    buffer += chunk
            else:
                num_speech_chunks = 0
                if speech_detected:
                    num_silent_chunks += 1
                    buffer += chunk
                    # Continue yielding chunks during short silences
                    yield base64.b64encode(chunk).decode('utf-8')

                    if num_silent_chunks > (SILENCE_DURATION * RATE) // CHUNK:
                        print("Speech ended, processing...")
                        # Yield any remaining buffer
                        if buffer:
                            yield base64.b64encode(buffer).decode('utf-8')
                        buffer = b''
                        speech_detected = False

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

# ... rest of the code remains the same ...

async def play_audio(audio_data):
    """Play audio data through speakers."""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    
    try:
        decoded_audio = base64.b64decode(audio_data)
        stream.write(decoded_audio)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

async def main():
    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await initialize_session(openai_ws)

        audio_capture_task = asyncio.create_task(handle_audio_input(openai_ws))
        openai_response_task = asyncio.create_task(handle_openai_responses(openai_ws))

        await asyncio.gather(audio_capture_task, openai_response_task)

async def safe_ws_send(ws, message):
    try:
        await ws.send(message)
    except Exception as e:
        logger.error(f"Error sending WebSocket message: {e}")

async def handle_audio_input(openai_ws):
    async for audio_chunk in capture_audio():
        audio_message = {
            "type": "input_audio_buffer.append",
            "audio": audio_chunk
        }
        await safe_ws_send(openai_ws, json.dumps(audio_message))
        
        # Send a message to indicate the end of the audio input
        end_message = {
            "type": "input_audio_buffer.flush"
        }
        await safe_ws_send(openai_ws, json.dumps(end_message))


async def handle_openai_responses(openai_ws):
    async for message in openai_ws:
        response = json.loads(message)
        if response['type'] in LOG_EVENT_TYPES:
            print(f"Received event: {response['type']}", response)

        if response.get('type') == 'response.audio.delta' and 'delta' in response:
            await play_audio(response['delta'])

async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

if __name__ == "__main__":
    asyncio.run(main())