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

// Dummy placeholder taaki missing key pe server crash na ho startup ke time —
// asli error tab aayega jab koi request /transcribe pe aayegi bina valid key ke.
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY || 'missing-key-set-env-file' });

app.post('/transcribe', upload.single('audio'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'Koi audio file nahi mili.' });
  }

  if (!process.env.GROQ_API_KEY) {
    if (req.file) fs.unlink(req.file.path, () => {});
    return res.status(500).json({ error: '.env file mein GROQ_API_KEY set nahi hai. .env.example dekho.' });
  }

  try {
    const transcription = await groq.audio.transcriptions.create({
      file: fs.createReadStream(req.file.path),
      model: 'whisper-large-v3',
      // language field hata bhi sakte ho — Whisper khud detect kar leta hai.
      // Hindi/Hinglish audio ke liye 'hi' try karo, English ke liye 'en'.
      language: 'en',
      response_format: 'json'
    });

    fs.unlink(req.file.path, () => {}); // temp file cleanup

    res.json({ text: transcription.text });
  } catch (err) {
    console.error('Groq Whisper error:', err.message);
    if (req.file) fs.unlink(req.file.path, () => {});
    res.status(500).json({ error: err.message });
  }
});

app.get('/', (req, res) => {
  res.send('Groq Whisper STT backend chal raha hai. POST /transcribe pe audio bhejo.');
});

// ---------- NLP / Answer generation via Groq LLM ----------
// Abhi ke liye seedha LLM se reply generate ho raha hai (RAG baad mein add hoga
// taaki jawab teacher ke actual notes se grounded ho).
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
      model: process.env.GROQ_MODEL || 'openai/gpt-oss-120b',
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

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`STT backend chal raha hai: http://localhost:${PORT}`);
});