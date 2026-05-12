"""
tests/test_speech.py
--------------------
Standalone test for speech recognition using the SpeechRecognition library.
Uses sr.Microphone() directly — the most reliable approach.

Run:
    python tests/test_speech.py
"""
import speech_recognition as sr
import sys

def main():
    r = sr.Recognizer()

    print("=== auhip Speech Recognition Test ===")
    print("Using Google Web Speech API")
    print()

    with sr.Microphone() as source:
        print("Adjusting for ambient noise... (1 second)")
        r.adjust_for_ambient_noise(source, duration=1)
        print(f"Energy threshold set to: {r.energy_threshold:.0f}")
        print()

        while True:
            print(">>> Say something! (Ctrl+C to quit)")
            try:
                audio = r.listen(source, timeout=10, phrase_time_limit=7)
                print("Processing...")

                try:
                    text = r.recognize_google(audio)
                    print(f"\n[RECOGNIZED]: \"{text}\"\n")
                except sr.UnknownValueError:
                    print("[RESULT]: Could not understand audio\n")
                except sr.RequestError as e:
                    print(f"[ERROR]: Google API error — {e}\n")

            except sr.WaitTimeoutError:
                print("[TIMEOUT]: No speech detected, waiting again...\n")
            except KeyboardInterrupt:
                print("\nExiting.")
                sys.exit(0)

if __name__ == "__main__":
    main()
