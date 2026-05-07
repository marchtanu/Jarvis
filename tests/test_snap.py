"""
tests/test_snap.py
------------------
Standalone test for double-snap detection.
Prints clearly when 1 or 2 snaps are detected.

Run:
    python tests/test_snap.py
"""
import numpy as np
import sounddevice as sd
import time
import sys

# ── Configuration ────────────────────────────────────────────────────────────
SAMPLERATE = 44100
BLOCK_SIZE = 1024
SNAP_THRESHOLD_MULTIPLIER = 6.0   # Increase to reduce false positives
SNAP_REFRACTORY_PERIOD    = 0.3   # Seconds to ignore after a snap
SNAP_WINDOW               = 2.0   # Max seconds between the two snaps
SOUND_THRESHOLD           = 0.01  # Log any sound above this energy

# ── State ────────────────────────────────────────────────────────────────────
energy_history = []
last_trigger_time = 0.0
last_snap_time = 0.0
snap_count = 0
last_sound_log_time = 0.0

def audio_callback(indata, frames, time_info, status):
    global energy_history, last_trigger_time, last_snap_time, snap_count, last_sound_log_time

    if status:
        print(f"[WARNING] {status}", file=sys.stderr)

    audio = indata[:, 0]  # Mono
    current_energy = float(np.sqrt(np.mean(audio ** 2)))
    now = time.time()

    # ── Sound detection log (throttled to 1/sec) ──────────────────────────
    if current_energy > SOUND_THRESHOLD and now - last_sound_log_time > 1.0:
        print(f"  [SOUND] Energy: {current_energy:.4f}")
        last_sound_log_time = now

    # ── Adaptive threshold ────────────────────────────────────────────────
    energy_history.append(current_energy)
    if len(energy_history) > 50:
        energy_history.pop(0)
    avg_energy = float(np.mean(energy_history))

    # ── Snap detection ────────────────────────────────────────────────────
    if (current_energy > avg_energy * SNAP_THRESHOLD_MULTIPLIER and
            now - last_trigger_time > SNAP_REFRACTORY_PERIOD):

        last_trigger_time = now

        if snap_count == 0:
            snap_count = 1
            last_snap_time = now
            print(f"\n[SNAP 1] Detected — waiting for second snap within {SNAP_WINDOW}s ...")

        elif snap_count == 1:
            gap = now - last_snap_time
            if gap <= SNAP_WINDOW:
                snap_count = 0
                print(f"\n{'='*40}")
                print(f"  !! DOUBLE SNAP DETECTED !!  (gap: {gap:.2f}s)")
                print(f"{'='*40}\n")
            else:
                # Too slow — treat this as a new first snap
                snap_count = 1
                last_snap_time = now
                print(f"\n[SNAP 1] (second was too slow {gap:.2f}s) — restarting ...")

def main():
    print("=== Jarvis Snap Detection Test ===")
    print(f"Threshold multiplier : {SNAP_THRESHOLD_MULTIPLIER}x")
    print(f"Snap window          : {SNAP_WINDOW}s")
    print(f"Refractory period    : {SNAP_REFRACTORY_PERIOD}s")
    print()
    print("Listening for snaps... Ctrl+C to quit.")
    print()

    try:
        with sd.InputStream(
            samplerate=SAMPLERATE,
            channels=1,
            blocksize=BLOCK_SIZE,
            callback=audio_callback,
        ):
            while True:
                # Check for snap_count timeout (reset to 0 if window expired)
                global snap_count, last_snap_time
                if snap_count == 1 and time.time() - last_snap_time > SNAP_WINDOW:
                    snap_count = 0
                    print("[TIMEOUT] No second snap — back to idle.\n")
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nExiting.")

if __name__ == "__main__":
    main()
