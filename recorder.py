import os
import queue
import time
import wave
from collections import deque

import sounddevice as sd
import webrtcvad

# CHANGE: "from config import *" ki jagah explicit imports.
# WHY:    pata rehta hai kya aa raha hai, aur names aapas mein takrate nahi.
from config import (
    SAMPLE_RATE, CHANNELS, DTYPE, FRAME_DURATION, FRAME_SIZE, VAD_MODE,
    MAX_SILENCE_DURATION, MAX_WAIT_FOR_SPEECH, MAX_RECORD_DURATION,
    PRE_SPEECH_BUFFER_MS, SPEECH_START_FRAMES, AUDIO_DIR, TEMP_AUDIO_FILE,
)


class Recorder:
    def __init__(self):
        # CHANGE: duplicate asserts hata diye (config.py pehle hi check karta hai).
        # CHANGE: getattr(self, "_unused") wala hack hata ke seedha config values use ki.
        self.vad = webrtcvad.Vad(VAD_MODE)
        self.audio_queue = queue.Queue()

    def callback(self, indata, frames, time_info, status):
        if status:
            print(status)
        self.audio_queue.put(bytes(indata))

    def _drain_queue(self):
        """
        CHANGE: naya. Purani bachi hui audio frames saaf karta hai.
        WHY:    pehle pichli recording ke frames queue mein reh jaate the aur agli
                recording ki shuruaat mein ghus jaate the.
        """
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                return

    def listen(self):
        print("🎤 Listening...")
        os.makedirs(AUDIO_DIR, exist_ok=True)
        self._drain_queue()

        audio_frames = []
        silence_frames = 0
        recording = False
        voiced_run = 0

        # pre-buffer mein SPEECH_START_FRAMES bhi jodte hain, kyunki wahi frames trigger karte hain
        pre_len = max(1, int(PRE_SPEECH_BUFFER_MS / FRAME_DURATION)) + SPEECH_START_FRAMES
        pre_buffer = deque(maxlen=pre_len)

        start_time = time.monotonic()
        record_start = None
        expected_bytes = FRAME_SIZE * 2   # int16 = 2 bytes per sample

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=FRAME_SIZE,
                dtype=DTYPE,
                channels=CHANNELS,
                callback=self.callback,
            ):
                while True:
                    # CHANGE: har baar chhota timeout (0.5s) + wall-clock deadlines.
                    # WHY:    pehle recording ke dauran timeout=None tha, mic stream mar jaye to
                    #         program hamesha latka rehta.
                    now = time.monotonic()
                    if not recording and now - start_time >= MAX_WAIT_FOR_SPEECH:
                        print("⌛ No speech detected, giving up.")
                        return None
                    if recording and now - record_start >= MAX_RECORD_DURATION:
                        print("⏱️ Max recording duration reached")
                        break

                    try:
                        frame = self.audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if len(frame) != expected_bytes:   # webrtcvad galat size pe crash karta hai
                        continue

                    is_speech = self.vad.is_speech(frame, SAMPLE_RATE)

                    if not recording:
                        pre_buffer.append(frame)
                        # CHANGE: ek frame ki jagah SPEECH_START_FRAMES lagataar frames chahiye.
                        # WHY:    ek akeli click / khansi se recording shuru ho jaati thi.
                        voiced_run = voiced_run + 1 if is_speech else 0
                        if voiced_run >= SPEECH_START_FRAMES:
                            print("🟢 Speech detected...")
                            recording = True
                            record_start = now
                            audio_frames.extend(pre_buffer)   # bolne se pehle ka hissa bhi
                            silence_frames = 0
                        continue

                    audio_frames.append(frame)
                    if is_speech:
                        silence_frames = 0
                    else:
                        silence_frames += 1
                        if silence_frames * FRAME_DURATION / 1000 >= MAX_SILENCE_DURATION:
                            print("🔴 Speech ended")
                            break

        except sd.PortAudioError as e:
            print(f"⚠️ Audio device error: {e}")
            if not audio_frames:
                return None

        if not audio_frames:
            return None

        with wave.open(TEMP_AUDIO_FILE, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(audio_frames))

        return TEMP_AUDIO_FILE