import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from scipy.signal import resample

RECORD_SECONDS = 5
MIC_DEVICE = 0
MIC_SAMPLE_RATE = 48000
NEMO_SAMPLE_RATE = 16000

print("Recording...")
print("Speak now!")

audio = sd.rec(
    int(RECORD_SECONDS * MIC_SAMPLE_RATE),
    samplerate=MIC_SAMPLE_RATE,
    channels=1,
    dtype="float32",
    device=MIC_DEVICE
)

sd.wait()

print("Recording complete!")

print("Converting audio to 16 kHz...")

num_samples = int(
    len(audio) * NEMO_SAMPLE_RATE / MIC_SAMPLE_RATE
)

audio_16k = resample(
    audio[:, 0],
    num_samples
)

audio_16k = np.clip(audio_16k, -1, 1)

audio_16k = np.int16(audio_16k * 32767)

write(
    "parakeet/recording.wav",
    NEMO_SAMPLE_RATE,
    audio_16k
)

print("Saved as parakeet/recording.wav")
