import sounddevice as sd
from scipy.io.wavfile import write

SAMPLE_RATE = 16000
DURATION = 5
DEVICE = 0

print("Recording...")
print("Speak now!")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    device=DEVICE
)

sd.wait()

write("recording.wav", SAMPLE_RATE, audio)

print("Recording complete!")
print("Saved as recording.wav")
