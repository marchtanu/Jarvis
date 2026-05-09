\

# Speech Recognition System

Jarvis features a hybrid speech recognition architecture that allows for both high-speed local processing and high-accuracy cloud processing.

## 1. Recognition Engines

### Local Engine: Vosk (Default)

- **Model:** `vosk-model-small-en-us-0.15`
- **Performance:** Ultra-low latency (near-instant).
- **Privacy:** 100% offline; no audio data leaves the machine.
- **Streaming:** Supports real-time partial results and continuous listening.

### Cloud Engine: Google Speech API (Fallback)

- **Library:** `SpeechRecognition`
- **Performance:** High accuracy but requires internet and has significant latency (1-3 seconds).
- **Privacy:** Audio is sent to Google for processing.

---

## 2. How to Switch Engines

The system is designed to be easily swappable. To switch between engines:

1. Open `jarvis/audio/speech_recognition.py`.
2. Locate the `__init__` method of the `SpeechRecognizer` class.
3. Change the `self._use_vosk` flag:
   - `self._use_vosk = True` (Default: Fast, Local)
   - `self._use_vosk = False` (Cloud: High Accuracy, Slow)

---

## 3. Advanced Feature: Vocabulary Locking (Grammar)

To solve the issue of "near-miss" mishearings (e.g., mishearing "daddy home" as "the home"), the system supports **Grammar Locking**.

### How it works:

When Jarvis is in a critical state (like waiting for a Wake Word), the `listen_for_command` method accepts a `grammar` list.

```python
# Example from state_machine.py
text = await self.speech_recognizer.listen_for_command(
    timeout=8.0,
    grammar=["daddy home", "exit"]
)
```

By providing this list, Vosk is forced to ignore the rest of the English dictionary and only match your voice against those specific words. This results in **nearly 100% accuracy** for activation commands.

---

## 4. Technical Implementation Details

- **Audio Format:** Vosk requires `int16` mono audio at the model's native sample rate (matching `config.SAMPLERATE`).
- **Stream Handling:** The `SpeechRecognizer` uses `sounddevice.RawInputStream` for local recognition to bypass standard OS overhead.
- **Fallback Logic:** The initialization logic for the Google API is preserved in comments within `initialize()` to prevent dependency bloat while allowing for quick restoration.
