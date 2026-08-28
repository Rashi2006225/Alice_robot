import nemo.collections.asr as nemo_asr

AUDIO_FILE = "audio/test.wav"

print("Loading ASR model...")

model = nemo_asr.models.ASRModel.from_pretrained(
    model_name="stt_en_conformer_ctc_small"
)

print("Transcribing audio...")

result = model.transcribe([AUDIO_FILE])

if isinstance(result, list):
    transcription = result[0]
else:
    transcription = result

if hasattr(transcription, "text"):
    transcription = transcription.text

print("\nTranscription:")
print(transcription)