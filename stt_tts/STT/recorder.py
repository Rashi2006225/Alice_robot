import os
import wave
import queue
import time
from collections import deque

import sounddevice as sd
import webrtcvad

from config import *


class Recorder:
    def __init__(self):
        # --- Hard requirements for webrtcvad ---
        assert CHANNELS == 1, "webrtcvad requires mono audio (CHANNELS must be 1)"
        assert SAMPLE_RATE in (8000, 16000, 32000, 48000), \
            "webrtcvad only supports 8000/16000/32000/48000 Hz"
        assert FRAME_DURATION in (10, 20, 30), \
            "webrtcvad only supports 10/20/30ms frames"

        expected_frame_size = int(SAMPLE_RATE * FRAME_DURATION / 1000)
        assert FRAME_SIZE == expected_frame_size, (
            f"FRAME_SIZE ({FRAME_SIZE}) must equal SAMPLE_RATE*FRAME_DURATION/1000 "
            f"({expected_frame_size}) for VAD to work correctly"
        )
        assert DTYPE == "int16", "VAD + wave output require int16 PCM"

        self.vad = webrtcvad.Vad(VAD_MODE)
        self.audio_queue = queue.Queue()

        # Optional config knobs — fall back to sane defaults if not defined in config.py
        self.max_wait_for_speech = getattr(self, "_unused", None) or globals().get(
            "MAX_WAIT_FOR_SPEECH", 10.0
        )  # seconds to wait for speech to start before giving up
        self.max_record_duration = globals().get(
            "MAX_RECORD_DURATION", 30.0
        )  # hard cap on utterance length, seconds
        self.pre_speech_ms = globals().get(
            "PRE_SPEECH_BUFFER_MS", 300
        )  # lookback buffer prepended once speech starts

    def callback(self, indata, frames, time_info, status):
        if status:
            print(status)
        self.audio_queue.put(bytes(indata))

    def listen(self):
        print("🎤 Listening...")
        os.makedirs("audio", exist_ok=True)

        audio_frames = []
        silence_frames = 0
        recording = False

        pre_buffer_maxlen = max(1, int(self.pre_speech_ms / FRAME_DURATION))
        pre_buffer = deque(maxlen=pre_buffer_maxlen)

        start_time = time.monotonic()

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=FRAME_SIZE,
                dtype=DTYPE,
                channels=CHANNELS,
                callback=self.callback,
            ):
                while True:
                    # Timeout while waiting for speech to begin
                    try:
                        wait_timeout = (
                            self.max_wait_for_speech
                            if not recording
                            else None  # once recording, don't time out on queue.get
                        )
                        frame = self.audio_queue.get(timeout=wait_timeout)
                    except queue.Empty:
                        print("⌛ No speech detected, giving up.")
                        return None

                    is_speech = self.vad.is_speech(frame, SAMPLE_RATE)

                    if is_speech:
                        if not recording:
                            print("🟢 Speech detected...")
                            recording = True
                            audio_frames.extend(pre_buffer)  # prepend lookback

                        audio_frames.append(frame)
                        silence_frames = 0

                    elif recording:
                        audio_frames.append(frame)
                        silence_frames += 1

                        if (
                            silence_frames * FRAME_DURATION / 1000
                            >= MAX_SILENCE_DURATION
                        ):
                            print("🔴 Speech ended")
                            break

                    else:
                        # Not recording yet — keep a rolling buffer so speech
                        # onset isn't clipped once VAD actually triggers.
                        pre_buffer.append(frame)

                    # Hard cap so a stuck/misclassified stream can't record forever
                    if recording and (
                        len(audio_frames) * FRAME_DURATION / 1000
                        >= self.max_record_duration
                    ):
                        print("⏱️ Max recording duration reached")
                        break

                    # Also cap total wait time even if is_speech never confirms
                    if not recording and (
                        time.monotonic() - start_time >= self.max_wait_for_speech
                    ):
                        print("⌛ No speech detected, giving up.")
                        return None

        except sd.PortAudioError as e:
            print(f"⚠️ Audio device error: {e}")
            if not audio_frames:
                return None
            # fall through and try to save whatever we captured

        if not audio_frames:
            return None

        with wave.open(TEMP_AUDIO_FILE, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(audio_frames))

        return TEMP_AUDIO_FILE
