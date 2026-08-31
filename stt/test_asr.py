# import sounddevice as sd
# import numpy as np
# from scipy.io.wavfile import write
# from scipy.signal import resample

# import nemo.collections.asr as nemo_asr


# # =========================
# # SETTINGS
# # =========================
# RECORD_SECONDS = 5
# MIC_DEVICE = 0
# MIC_SAMPLE_RATE = 48000
# NEMO_SAMPLE_RATE = 16000

# MODEL_PATH = "/home/radhika/.cache/torch/NeMo/NeMo_3.0.0/stt_en_conformer_ctc_small/5d2d8e5b2b5adb8f5091363c6ba19c55/stt_en_conformer_ctc_small.nemo"


# # =========================
# # RECORD AUDIO
# # =========================
# print("Recording...")
# print("Speak now!")

# audio = sd.rec(
#     int(RECORD_SECONDS * MIC_SAMPLE_RATE),
#     samplerate=MIC_SAMPLE_RATE,
#     channels=1,
#     dtype="float32",
#     device=MIC_DEVICE
# )

# sd.wait()

# print("Recording complete!")


# # =========================
# # RESAMPLE 48 kHz -> 16 kHz
# # =========================
# print("Converting audio to 16 kHz...")

# num_samples = int(
#     len(audio) * NEMO_SAMPLE_RATE / MIC_SAMPLE_RATE
# )

# audio_16k = resample(
#     audio[:, 0],
#     num_samples
# )

# audio_16k = np.clip(audio_16k, -1, 1)
# audio_16k = np.int16(audio_16k * 32767)

# write(
#     "recording.wav",
#     NEMO_SAMPLE_RATE,
#     audio_16k
# )

# print("Saved as recording.wav")


# # =========================
# # LOAD LOCAL NeMo MODEL
# # =========================
# print("Loading ASR model...")

# model = nemo_asr.models.EncDecCTCModel.restore_from(
#     restore_path=MODEL_PATH
# )

# print("ASR model loaded successfully!")


# # =========================
# # TRANSCRIBE
# # =========================
# print("Transcribing...")

# result = model.transcribe(
#     ["recording.wav"]
# )

# print("\n========== TRANSCRIPTION ==========")
# print(result[0])
# print("===================================")
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from scipy.signal import resample

import nemo.collections.asr as nemo_asr


# =========================
# SETTINGS
# =========================
MIC_DEVICE = 0

MIC_SAMPLE_RATE = 48000
NEMO_SAMPLE_RATE = 16000

CHANNELS = 1

# Voice detection settings
BLOCK_DURATION = 0.1          # 100 ms
SILENCE_DURATION = 1.0        # Stop after 1 sec silence
MAX_RECORD_SECONDS = 15       # Safety limit

# How loud speech needs to be
# We will tune this after testing
ENERGY_THRESHOLD = 0.015

MODEL_PATH = (
    "/home/radhika/.cache/torch/NeMo/NeMo_3.0.0/"
    "stt_en_conformer_ctc_small/"
    "5d2d8e5b2b5adb8f5091363c6ba19c55/"
    "stt_en_conformer_ctc_small.nemo"
)


# =========================
# RECORD UNTIL SILENCE
# =========================
def record_until_silence():

    block_size = int(MIC_SAMPLE_RATE * BLOCK_DURATION)

    audio_chunks = []

    silence_blocks = 0
    max_blocks = int(MAX_RECORD_SECONDS / BLOCK_DURATION)
    silence_limit = int(SILENCE_DURATION / BLOCK_DURATION)

    print("\n===================================")
    print("🎤 Listening...")
    print("Speak now!")
    print("===================================")

    # First wait for speech
    speech_started = False

    with sd.InputStream(
        samplerate=MIC_SAMPLE_RATE,
        device=MIC_DEVICE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=block_size
    ) as stream:

        for _ in range(max_blocks):

            data, overflowed = stream.read(block_size)

            chunk = data[:, 0].copy()

            # Calculate volume / energy
            energy = np.sqrt(np.mean(chunk ** 2))

            if energy > ENERGY_THRESHOLD:

                # Speech detected
                speech_started = True
                silence_blocks = 0

                print("🗣️ Speech detected...", end="\r")

            elif speech_started:

                # Silence after speech
                silence_blocks += 1

            # Save audio only after speech starts
            if speech_started:
                audio_chunks.append(chunk)

            # Stop after enough silence
            if speech_started and silence_blocks >= silence_limit:
                break

    if not audio_chunks:
        print("\n❌ No speech detected.")
        return None

    audio = np.concatenate(audio_chunks)

    print("\n✅ Recording complete!")

    return audio


# =========================
# RECORD
# =========================
audio = record_until_silence()

if audio is None:
    exit()


# =========================
# RESAMPLE 48 kHz -> 16 kHz
# =========================
print("Converting audio to 16 kHz...")

num_samples = int(
    len(audio) * NEMO_SAMPLE_RATE / MIC_SAMPLE_RATE
)

audio_16k = resample(
    audio,
    num_samples
)

audio_16k = np.clip(audio_16k, -1, 1)

audio_16k = np.int16(
    audio_16k * 32767
)


# =========================
# SAVE AUDIO
# =========================
write(
    "recording.wav",
    NEMO_SAMPLE_RATE,
    audio_16k
)

print("Saved as recording.wav")


# =========================
# LOAD LOCAL NeMo MODEL
# =========================
print("Loading ASR model...")

model = nemo_asr.models.EncDecCTCModel.restore_from(
    restore_path=MODEL_PATH
)

print("ASR model loaded successfully!")


# =========================
# TRANSCRIBE
# =========================
print("Transcribing...")

result = model.transcribe(
    ["recording.wav"]
)


# =========================
# DISPLAY RESULT
# =========================
print("\n========== TRANSCRIPTION ==========")

print(result[0])

print("===================================")