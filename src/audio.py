import os
import wave
import struct
import math
import winsound
import threading

AUDIO_HI_BYTES = None
AUDIO_LO_BYTES = None

def generate_and_preload_studio_click_wavs():
    global AUDIO_HI_BYTES, AUDIO_LO_BYTES
    base_dir = os.path.dirname(os.path.abspath(__file__))
    hi_path = os.path.join(base_dir, "click_hi.wav")
    lo_path = os.path.join(base_dir, "click_lo.wav")
    
    sample_rate = 44100
    
    if not os.path.exists(hi_path):
        duration = 0.030
        num_samples = int(sample_rate * duration)
        with wave.open(hi_path, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            for i in range(num_samples):
                t = float(i) / sample_rate
                env = math.exp(-t * 180)
                val = int(28000 * math.sin(2 * math.pi * 1600 * t) * env)
                f.writeframes(struct.pack('<h', max(-32768, min(32767, val))))
                
    if not os.path.exists(lo_path):
        duration = 0.025
        num_samples = int(sample_rate * duration)
        with wave.open(lo_path, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            for i in range(num_samples):
                t = float(i) / sample_rate
                env = math.exp(-t * 220)
                val = int(20000 * math.sin(2 * math.pi * 900 * t) * env)
                f.writeframes(struct.pack('<h', max(-32768, min(32767, val))))

    try:
        with open(hi_path, 'rb') as f:
            AUDIO_HI_BYTES = f.read()
        with open(lo_path, 'rb') as f:
            AUDIO_LO_BYTES = f.read()
    except Exception as e:
        print("Error pre-cargando audio:", e)

def play_click(is_accent=False, enable_sound=True):
    if not enable_sound:
        return
    def _click():
        try:
            data = AUDIO_HI_BYTES if is_accent else AUDIO_LO_BYTES
            if data:
                winsound.PlaySound(data, winsound.SND_MEMORY)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                sound_file = os.path.join(base_dir, "click_hi.wav" if is_accent else "click_lo.wav")
                winsound.PlaySound(sound_file, winsound.SND_FILENAME)
        except Exception as e:
            print("Error audio:", e)
    threading.Thread(target=_click, daemon=True).start()

generate_and_preload_studio_click_wavs()
