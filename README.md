# WhisperOverlay

**Real-time speech transcription overlay for Windows** — powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (local CUDA) and Azure Speech Services.

Transcribes your voice word-by-word as you speak, injects text into any active window, and translates on the fly.

---

## Features

- **Always-on-top overlay** — floats above all windows, frameless, fully transparent background
- **Word-by-word live transcription** — text appears in the panel as each word is spoken (~400ms latency on GPU)
- **Auto-inject into active window** — typed text appears wherever your cursor is, like a voice input
- **Two recording modes** — Toggle (click once to start, click again to stop) or Push-to-talk (hold = record, release = stop)
- **Global hotkey** — works even when the overlay is not focused (default: `F9`, configurable)
- **Translation** — Russian → English + German via Azure Translator (shown in panel + injected)
- **Dual backend** — Local faster-whisper (CUDA/CPU) or Azure Speech Services
- **Resizable & draggable** — drag anywhere, resize from the corner, toggle transcript panel
- **Dark modern UI** — glassmorphism card, pulsing mic button animation, dark theme
- **Settings dialog** — configure model, device, hotkey, Azure keys, recording mode, opacity

---

## Requirements

- Windows 10/11
- Python 3.10+
- NVIDIA GPU with CUDA (recommended) — works on CPU too, just slower
- PyTorch with CUDA support

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/ArseniiB-o/whisper-overlay.git
cd whisper-overlay

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

> **First launch:** faster-whisper will download the model (~250MB for `small`) automatically.

---

## Configuration

Click **⚙** in the overlay to open Settings.

### General settings

| Setting | Description |
|---|---|
| Backend | `Local` (faster-whisper) or `Azure Speech Services` |
| Model | `tiny` / `base` / `small` (default) / `medium` / `large-v3` |
| Device | `cuda` (GPU, fast) or `cpu` |
| Language | Source language of your speech |
| Recording mode | **Toggle** or **Push-to-talk** |
| Translation | Enable and choose target languages (EN / DE) |
| Auto-inject | Paste transcribed text into the active window |
| Opacity | Window transparency |

### Azure Setup (optional)

If you want to use Azure Speech Services or Azure Translator:

1. **Speech-to-Text:** [portal.azure.com](https://portal.azure.com) → Create resource → **Speech** → copy **Key** and **Region**
2. **Translation:** [portal.azure.com](https://portal.azure.com) → Create resource → **Translator** → copy **Key** and **Region**
3. Enter keys in Settings → Azure tab

> Azure Speech provides real-time streaming STT. Azure Translator supports 100+ languages.

---

## Usage

| Action | Result |
|---|---|
| Click 🎙 | Toggle recording (Toggle mode) |
| Hold 🎙 | Record while held, stop on release (PTT mode) |
| `F9` | Same as clicking the mic (configurable) |
| `▾ / ▸` | Show/hide transcript panel |
| `⚙` | Open settings |
| Drag window | Move overlay anywhere |
| Drag corner | Resize overlay |

---

## How it works

```
Microphone → sounddevice stream
    ↓ (every 400ms, last 8s)
faster-whisper (CUDA) → partial text → live label + inject diff
    ↓ (on stop)
faster-whisper → final text → transcript + inject remaining
    ↓ (if translation enabled)
Azure Translator → translated text → transcript + inject
```

---

## Project structure

```
whisper-overlay/
├── main.py                    # Entry point
├── requirements.txt
├── core/
│   ├── audio.py               # sounddevice capture with peek() for live transcription
│   ├── transcriber_local.py   # faster-whisper wrapper
│   ├── transcriber_azure.py   # Azure Speech SDK wrapper
│   └── translator.py          # Azure Translator REST API
├── ui/
│   ├── overlay.py             # Main overlay window (PyQt6)
│   ├── settings_dialog.py     # Settings dialog
│   └── styles.py              # QSS dark theme
└── utils/
    ├── config.py              # JSON config with deep merge
    ├── hotkey.py              # Global hotkey via pynput
    └── injector.py            # Text injection with AttachThreadInput focus trick
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `PyQt6` | UI framework |
| `faster-whisper` | Local speech recognition (CTranslate2) |
| `sounddevice` | Audio capture |
| `pynput` | Global hotkeys + text injection |
| `pywin32` | Windows focus management (AttachThreadInput) |
| `azure-cognitiveservices-speech` | Azure Speech SDK |
| `requests` | Azure Translator REST API |

---

## License

MIT — do whatever you want with it.
