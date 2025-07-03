import asyncio
import websockets
import wave
import numpy as np
import tempfile
import torch
import whisper
import os
import scipy.signal


connected_clients = set()
stt_model = whisper.load_model("base")  # You can use "tiny" or "small" for faster response

# Constants for 10 sec chunk
CHUNK_DURATION_SEC = 10
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2  # 16-bit audio
CHUNK_SIZE = SAMPLE_RATE * BYTES_PER_SAMPLE * CHUNK_DURATION_SEC  # = 320000 bytes

async def handle_audio(websocket):
    print("Client connected")
    connected_clients.add(websocket)
    buffer = bytearray()
    try:
        async for message in websocket:
            buffer.extend(message)
            while len(buffer) >= CHUNK_SIZE:
                # Convert bytes to numpy array (int16)
                audio = np.frombuffer(buffer[:CHUNK_SIZE], dtype=np.int16)
                # Assume original sample rate is 48000 (check your browser's AudioContext sampleRate!)
                orig_sr = 48000
                # Resample to 16000
                audio_resampled = scipy.signal.resample_poly(audio, 16000, orig_sr)
                audio_resampled = audio_resampled.astype(np.int16)
                # Write to temp wav
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                    with wave.open(temp_wav.name, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(BYTES_PER_SAMPLE)
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes(audio_resampled.tobytes())
                transcript = await transcribe_audio(temp_wav.name)
                await broadcast_output(transcript)
                os.remove(temp_wav.name)
                buffer = buffer[CHUNK_SIZE:]
    finally:
        connected_clients.remove(websocket)

async def transcribe_audio(path):
    try:
        result = stt_model.transcribe(path, language="en")
        return result["text"].strip() or "(silence)"
    except Exception as e:
        return f"[Error] {e}"

async def broadcast_output(message):
    for client in connected_clients:
        try:
            await client.send(message)
        except:
            pass

async def main():
    async with websockets.serve(handle_audio, "localhost", 7000):
        print("✅ WebSocket server running at ws://localhost:7000")
        await asyncio.Future()

asyncio.run(main())
