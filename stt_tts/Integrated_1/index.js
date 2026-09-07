require('dotenv').config();
const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const Groq = require('groq-sdk');

const app = express();
app.use(cors());
app.use(express.json());

if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

// ---------------------------------------------------------------------------
// Config (mirrors the Python config.py / tts_config.py you sent — same knobs,
// just read from .env here instead of a Python module)
// ---------------------------------------------------------------------------
const STT_MODEL = process.env.STT_MODEL || 'whisper-large-v3-turbo';
const STT_LANGUAGE = process.env.STT_LANGUAGE || 'en'; // set to '' to let Whisper auto-detect

const GROQ_CHAT_MODEL = process.env.GROQ_MODEL || 'openai/gpt-oss-120b';

const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY;
const ELEVENLABS_VOICE_ID = process.env.ELEVENLABS_VOICE_ID || 'JBFqnCBsd6RMkjVDRZzb'; // George
const ELEVENLABS_MODEL_ID = process.env.ELEVENLABS_MODEL_ID || 'eleven_flash_v2_5';

// audio temporarily saved yahan, transcribe hote hi delete ho jayega
// diskStorage se filename mein extension preserve karte hain (.webm) —
// warna Groq file type detect nahi kar paata aur 400 error deta hai.
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, 'uploads/'),
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname);
  }
});
const upload = multer({ storage });

if (!process.env.GROQ_API_KEY) {
  console.warn('WARNING: GROQ_API_KEY .env file mein set nahi hai. .env.example dekho.');
}
if (!ELEVENLABS_API_KEY) {
  console.warn('WARNING: ELEVENLABS_API_KEY .env file mein set nahi hai. /speak 500 dega jab tak set na ho.');
}

// Dummy placeholder taaki missing key pe server crash na ho startup ke time —
// asli error tab aayega jab koi request /transcribe pe aayegi bina valid key ke.
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY || 'missing-key-set-env-file' });

// ---------------------------------------------------------------------------
// STT — same Groq Whisper flow as before, now driven by STT_MODEL/STT_LANGUAGE
// so it matches the Python GroqSTT config (whisper-large-v3-turbo by default).
// ---------------------------------------------------------------------------
app.post('/transcribe', upload.single('audio'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'Koi audio file nahi mili.' });
  }

  if (!process.env.GROQ_API_KEY) {
    fs.unlink(req.file.path, () => {});
    return res.status(500).json({ error: '.env file mein GROQ_API_KEY set nahi hai. .env.example dekho.' });
  }

  // empty-file guard, same idea as the Python transcribe() check
  const stat = fs.statSync(req.file.path);
  if (stat.size === 0) {
    fs.unlink(req.file.path, () => {});
    return res.status(400).json({ error: 'Audio file khali hai.' });
  }

  try {
    const transcriptionParams = {
      file: fs.createReadStream(req.file.path),
      model: STT_MODEL,
      response_format: 'verbose_json'
    };
    if (STT_LANGUAGE) transcriptionParams.language = STT_LANGUAGE;

    const transcription = await groq.audio.transcriptions.create(transcriptionParams);

    fs.unlink(req.file.path, () => {}); // temp file cleanup

    const text = (transcription.text || '').trim();
    if (!text) {
      return res.status(200).json({ text: '', warning: 'No speech detected in audio' });
    }

    res.json({ text });
  } catch (err) {
    console.error('Groq Whisper error:', err.message);
    if (req.file) fs.unlink(req.file.path, () => {});
    res.status(500).json({ error: err.message });
  }
});

app.get('/', (req, res) => {
  res.send('ALICE backend chal raha hai. POST /transcribe, /chat, /speak.');
});

// ---------------------------------------------------------------------------
// NLP / Answer generation via Groq LLM — unchanged
// ---------------------------------------------------------------------------
app.post('/chat', async (req, res) => {
  const { message } = req.body || {};

  if (!message || !message.trim()) {
    return res.status(400).json({ error: 'message field khali hai.' });
  }

  if (!process.env.GROQ_API_KEY) {
    return res.status(500).json({ error: '.env file mein GROQ_API_KEY set nahi hai. .env.example dekho.' });
  }

  try {
    const completion = await groq.chat.completions.create({
      model: GROQ_CHAT_MODEL,
      messages: [
        {
          role: 'system',
          content:
            "Tum ALICE ho, ek friendly service robot avatar jo college project ka demo hai. " +
            "Chhote, natural, spoken-style replies do (2-3 sentences se zyada mat karna, kyunki ye TTS se bola jayega). " +
            "User jis language/style (Hindi, English, ya Hinglish) mein baat kare, usi mein reply do. " +
            "Agar kuch pata na ho to seedha bol do ki pata nahi, bana ke mat batana."
        },
        { role: 'user', content: message }
      ],
      temperature: 0.7,
      max_tokens: 200
    });

    const reply = completion.choices[0]?.message?.content?.trim()
      || 'Mujhe samajh nahi aaya, dobara bol sakte hain?';

    res.json({ reply });
  } catch (err) {
    console.error('Groq chat error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// TTS — new. Same idea as the Python TTS class you sent (ElevenLabs,
// eleven_flash_v2_5, mp3_44100_128), just called over plain REST from Node
// so we don't need an extra SDK dependency. Streams mp3 bytes straight to
// the browser, which plays them with an <audio> element.
// ---------------------------------------------------------------------------
app.post('/speak', async (req, res) => {
  const { text, voice_id, model_id } = req.body || {};

  if (!text || !text.trim()) {
    return res.status(400).json({ error: 'text field khali hai.' });
  }
  if (!ELEVENLABS_API_KEY) {
    return res.status(500).json({ error: '.env file mein ELEVENLABS_API_KEY set nahi hai.' });
  }

  const voiceId = voice_id || ELEVENLABS_VOICE_ID;
  const modelId = model_id || ELEVENLABS_MODEL_ID;

  try {
    const elResponse = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}?output_format=mp3_44100_128`,
      {
        method: 'POST',
        headers: {
          'xi-api-key': ELEVENLABS_API_KEY,
          'Content-Type': 'application/json',
          'Accept': 'audio/mpeg'
        },
        body: JSON.stringify({
          text,
          model_id: modelId
        })
      }
    );

    if (!elResponse.ok) {
      const errBody = await elResponse.text();
      console.error('ElevenLabs TTS error:', elResponse.status, errBody);
      return res.status(502).json({ error: `ElevenLabs error (${elResponse.status})` });
    }

    res.set('Content-Type', 'audio/mpeg');
    const buffer = Buffer.from(await elResponse.arrayBuffer());
    res.send(buffer);
  } catch (err) {
    console.error('TTS request failed:', err.message);
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`ALICE backend chal raha hai: http://localhost:${PORT}`);
});
