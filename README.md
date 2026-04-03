# 🎙️ MoM Generator Bot

> **Meeting Recording → Minutes of Meeting (MoM) Auto Generator**
> Hindi + English + Hinglish support | 2+ ghante ki meetings | PDF/Word/Markdown export

[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?logo=streamlit)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-Whisper+GPT4-green?logo=openai)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🤔 Ye Kya Hai?

Agar tumhare paas meeting ki recording hai (video ya audio), toh ye bot:

1. **Recording le leta hai** (MP4, MKV, MOV, MP3, WAV, etc.)
2. **Audio nikalta hai** (FFmpeg se)
3. **Transcript banata hai** (OpenAI Whisper se - Hindi+English both)
4. **MoM generate karta hai** (GPT-4 se structured document)
5. **PDF/Word/Markdown mein export karta hai**

Sab kuch **automatic** - tum sirf file upload karo aur MoM ready!

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🎬 **Video Support** | MP4, MKV, AVI, MOV, WEBM |
| 🎵 **Audio Support** | MP3, WAV, M4A, OGG, FLAC |
| ⏰ **Long Meetings** | 2+ hours - chunked processing |
| 🗣️ **Languages** | Hindi, English, Hinglish (mixed) |
| 👥 **Participants** | Auto-detect from conversation |
| 📋 **MoM Sections** | Date, Duration, Participants, Action Items, Decisions, Open Issues, Next Steps |
| 📄 **Export Formats** | PDF, Word (.docx), Markdown (.md) |
| 🌐 **Web UI** | Streamlit - drag & drop |
| 💻 **CLI** | Command line - automation ke liye |

---

## 📁 Project Structure

```
Mom/
├── app.py                    # 🌐 Streamlit Web UI
├── main.py                   # 💻 CLI version
├── requirements.txt          # 📦 Dependencies
├── .env.example              # 🔐 Environment template
├── README.md                 # 📖 Ye file
├── src/
│   ├── __init__.py
│   ├── audio_extractor.py    # 🔊 FFmpeg audio extraction
│   ├── transcriber.py        # 🎤 Whisper transcription
│   ├── summarizer.py         # 🤖 GPT MoM generation
│   ├── document_generator.py # 📄 PDF/Word/MD export
│   └── utils.py              # 🛠️ Helper functions
├── templates/
│   └── mom_template.html     # 🎨 HTML MoM template
├── outputs/                  # 📂 Generated files (gitignored)
└── uploads/                  # 📂 Temp uploads (gitignored)
```

---

## 🚀 Installation

### Prerequisites

1. **Python 3.9+** install karo
2. **FFmpeg** install karo:
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg

   # macOS
   brew install ffmpeg

   # Windows
   # Download from: https://ffmpeg.org/download.html
   # PATH mein add karo
   ```

### Setup Steps

```bash
# 1. Repository clone karo
git clone https://github.com/singhshabnam042/Mom.git
cd Mom

# 2. Virtual environment banao (recommended)
python -m venv venv
source venv/bin/activate   # Linux/Mac
# ya
venv\Scripts\activate      # Windows

# 3. Dependencies install karo
pip install -r requirements.txt

# 4. Environment variables setup karo
cp .env.example .env
# .env file open karo aur OPENAI_API_KEY fill karo
```

### .env File Setup

```env
OPENAI_API_KEY=sk-your-api-key-here
GPT_MODEL=gpt-4
WHISPER_MODEL=medium
```

> 💡 **API Key kahan se milega?** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

---

## 💻 Usage

### Option 1: Web UI (Streamlit) - Recommended

```bash
streamlit run app.py
```

Browser mein `http://localhost:8501` open hoga.

**Steps:**
1. Sidebar mein OpenAI API key enter karo
2. Whisper model choose karo (medium recommended)
3. Recording file drag & drop karo
4. "Generate MoM" button dabao
5. MoM preview dekho
6. PDF/Word/Markdown download karo

### Option 2: CLI (Command Line)

```bash
# Basic usage
python main.py --input meeting.mp4

# Custom output name
python main.py --input meeting.mp4 --output board_meeting_jan2024

# Specific format
python main.py --input meeting.mp3 --format docx

# Saare formats generate karo
python main.py --input meeting.mp4 --format all

# Hindi meeting ke liye large model use karo
python main.py --input hindi_meeting.mp4 --whisper-model large --language hi

# Transcript bhi save karo
python main.py --input meeting.mp4 --save-transcript

# Sirf transcript (no GPT, no API key needed)
python main.py --input meeting.mp4 --transcript-only

# Verbose mode (debugging ke liye)
python main.py --input meeting.mp4 --verbose
```

**CLI Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--input, -i` | Required | Input file path |
| `--output, -o` | Auto | Output filename (no extension) |
| `--format, -f` | `pdf` | `pdf`, `docx`, `markdown`, `all` |
| `--output-dir` | `outputs/` | Output directory |
| `--whisper-model` | `medium` | Whisper model size |
| `--gpt-model` | `gpt-4` | GPT model |
| `--language` | Auto | `hi`, `en`, or empty |
| `--api-key` | `.env` | OpenAI API key |
| `--save-transcript` | Off | Transcript bhi save karo |
| `--transcript-only` | Off | Sirf transcript |
| `--verbose, -v` | Off | Debug output |

---

## 📋 MoM Output Format

```
📅 MEETING DATE & TIME
Meeting Date: 2024-01-15

⏱️ DURATION
45 minutes 30 seconds

👥 PARTICIPANTS IDENTIFIED
- Shabnam Singh
- Rahul Sharma
- Priya Verma

📌 KEY DISCUSSION POINTS
1. Project deadline extended to March 30th
2. New UI design approved by client
3. Budget revision discussed and approved

✅ ACTION ITEMS
1. Shabnam: Send updated wireframes by Friday
2. Rahul: Setup staging server by Monday
3. Priya: Client follow-up call on Wednesday

📝 DECISIONS MADE
1. React Native for mobile app development
2. Weekly sync every Tuesday at 3 PM
3. Budget increased by 20%

⚠️ OPEN ISSUES / PENDING ITEMS
1. API documentation still pending
2. Third-party vendor response awaited
3. Security audit schedule not finalized

📆 NEXT STEPS / FOLLOW-UPS
1. Next meeting: January 22, 2024 at 3 PM
2. All action items due by January 19
3. Final review before client presentation
```

---

## ⚙️ Configuration Options

### Whisper Model Selection

| Model | Size | Speed | Accuracy | Hindi Quality |
|-------|------|-------|----------|---------------|
| `tiny` | 39 MB | ⚡⚡⚡ | ⭐⭐ | ⭐ |
| `base` | 74 MB | ⚡⚡⚡ | ⭐⭐⭐ | ⭐⭐ |
| `small` | 244 MB | ⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| `medium` | 769 MB | ⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `large` | 1550 MB | ⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `large-v2` | 1550 MB | ⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation:**
- Short English meetings: `small` ya `medium`
- Hindi/Hinglish meetings: `medium` ya `large`
- Best accuracy: `large-v2` ya `large-v3`

### GPT Model Selection

| Model | Cost | Quality | Speed |
|-------|------|---------|-------|
| `gpt-3.5-turbo` | Low | Good | Fast |
| `gpt-4` | Medium | Best | Medium |
| `gpt-4-turbo` | Medium | Best | Fast |

---

## 🔧 Troubleshooting

### ❌ "FFmpeg nahi mila"
```bash
# Ubuntu
sudo apt update && sudo apt install ffmpeg -y

# macOS
brew install ffmpeg

# Check karo
ffmpeg -version
```

### ❌ "OpenAI API key nahi mili"
```bash
# .env file check karo
cat .env

# Ya environment variable set karo
export OPENAI_API_KEY=sk-your-key-here
```

### ❌ "openai-whisper install nahi hai"
```bash
pip install openai-whisper
# Ya agar PyTorch nahi hai
pip install openai-whisper torch
```

### ❌ Transcript empty aa raha hai
1. Audio file check karo - kya sound hai?
2. Large model try karo: `--whisper-model large`
3. Language explicitly set karo: `--language hi` ya `--language en`
4. File format check karo - WAV best hai

### ❌ GPT API error / Rate limit
1. API key valid hai? `platform.openai.com` check karo
2. Credit available hai? Billing section check karo
3. GPT-3.5 try karo (cheaper): `--gpt-model gpt-3.5-turbo`

### ❌ Memory error (large model)
```bash
# Smaller model use karo
python main.py --input meeting.mp4 --whisper-model small
```

### ❌ Long meeting mein kuch miss ho raha hai
```bash
# Large model use karo + save transcript for verification
python main.py --input meeting.mp4 --whisper-model large --save-transcript
```

---

## 💡 Tips & Tricks

1. **Best Audio Quality ke liye:** WAV format best hai transcription ke liye
2. **Hindi meetings:** `--whisper-model large` use karo for best accuracy
3. **Long meetings (2+ hours):** Automatically chunks mein split hota hai
4. **Batch processing:** Shell script se multiple files process karo
5. **API costs bachao:** Draft ke liye `gpt-3.5-turbo`, final ke liye `gpt-4`

### Batch Processing Example

```bash
#!/bin/bash
# batch_process.sh
for file in recordings/*.mp4; do
    echo "Processing: $file"
    python main.py --input "$file" --format all --whisper-model medium
done
```

---

## 🔐 Security Notes

- API key kabhi code mein hardcode mat karo
- `.env` file `.gitignore` mein hai - safe hai
- `outputs/` aur `uploads/` directories gitignored hain
- Sensitive meeting recordings ko securely handle karo

---

## 📦 Dependencies

```
openai-whisper    # Speech-to-text (by OpenAI)
openai            # GPT API client
ffmpeg-python     # FFmpeg wrapper
pydub             # Audio processing
streamlit         # Web UI
fpdf2             # PDF generation
python-docx       # Word document generation
python-dotenv     # .env file support
tqdm              # Progress bars
numpy             # Numerical computing
```

---

## 🤝 Contributing

1. Fork karo
2. Feature branch banao: `git checkout -b feature/amazing-feature`
3. Changes karo aur commit karo
4. Push karo: `git push origin feature/amazing-feature`
5. Pull Request open karo

---

## 📝 License

MIT License - freely use, modify, distribute karo.

---

## 🙏 Credits

- **OpenAI Whisper** - Amazing speech recognition
- **OpenAI GPT-4** - Intelligent text summarization
- **FFmpeg** - Media processing powerhouse
- **Streamlit** - Beautiful Python web apps
- Built with ❤️ for the community

---

*Agar kuch problem aaye toh issue raise karo - help milegi! 🚀*