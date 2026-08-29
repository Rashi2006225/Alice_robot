import nemo.collections.asr as nemo_asr


MODEL_PATH = "/home/radhika/Desktop/AI_teacher/parakeet/models/parakeet-tdt-0.6b-v3.nemo"
AUDIO_PATH = "/home/radhika/Desktop/AI_teacher/parakeet/recording.wav"


print("Loading Parakeet model...")

model = nemo_asr.models.EncDecRNNTBPEModel.restore_from(
    restore_path=MODEL_PATH
)

print("Parakeet model loaded successfully!")

print("Transcribing...")

result = model.transcribe(
    [AUDIO_PATH],
    batch_size=1
)

print("\n========== PARAKEET TRANSCRIPTION ==========")
print(result[0])
print("============================================")