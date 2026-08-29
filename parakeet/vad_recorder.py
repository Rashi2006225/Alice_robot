import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from scipy.signal import resample

MIC_DEVICE = 0
MIC_SAMPLE_RATE = 48000
NEMO_SAMPLE_RATE = 16000

BLOCK_DURATION = 0.1
BLOCK_SIZE = int(MIC_SAMPLE_RATE * BLOCK_DURATION)

ENERGY_THRESHOLD = 0.02
SILENCE_DURATION = 1.2
MIN_RECORDING_TIME = 2.0
MAX_RECORDING_TIME = 15.0

print("====================================")
print("      PARAKEET VOICE RECORDER")
print("====================================")
print("Listening...")
print("Speak naturally.")
print("Waiting for speech...")
print(f"Microphone sample rate: {MIC_SAMPLE_RATE} Hz")

audio_chunks = []
speech_started = False
silence_time = 0
recording_time = 0

with sd.InputStream(
    samplerate=MIC_SAMPLE_RATE,
    blocksize=BLOCK_SIZE,
    channels=1,
    dtype="float32",
    device=MIC_DEVICE,
    latency="high"
) as stream:

    while True:
        audio, overflowed = stream.read(BLOCK_SIZE)

        if overflowed:
            continue

        audio = audio[:, 0]

        rms = np.sqrt(np.mean(audio ** 2))

        if not speech_started:

            if rms > ENERGY_THRESHOLD:
                speech_started = True
                print("Speech detected!")

                audio_chunks.append(audio.copy())
                recording_time += BLOCK_DURATION

        else:

            audio_chunks.append(audio.copy())
            recording_time += BLOCK_DURATION

            if rms > ENERGY_THRESHOLD:
                silence_time = 0
            else:
                silence_time += BLOCK_DURATION

            if (
                recording_time >= MIN_RECORDING_TIME
                and silence_time >= SILENCE_DURATION
            ):
                print("Speech finished.")
                break

            if recording_time >= MAX_RECORDING_TIME:
                print("Maximum recording time reached.")
                break

if not audio_chunks:
    print("No speech detected.")
    exit()

print("Processing audio...")

audio = np.concatenate(audio_chunks)

num_samples = int(
    len(audio) * NEMO_SAMPLE_RATE / MIC_SAMPLE_RATE
)

audio_16k = resample(
    audio,
    num_samples
)

audio_16k = np.clip(audio_16k, -1, 1)
audio_16k = np.int16(audio_16k * 32767)

output_file = "parakeet/recording.wav"

write(
    output_file,
    NEMO_SAMPLE_RATE,
    audio_16k
)

duration = len(audio_16k) / NEMO_SAMPLE_RATE

print(f"Saved: {output_file}")
print(f"Duration: {duration:.2f} seconds")
print("Ready for Parakeet.")