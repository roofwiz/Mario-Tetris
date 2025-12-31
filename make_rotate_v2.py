import wave
import math
import struct
import random

def save_wav(filename, data):
    with wave.open(filename, 'w') as w:
        w.setparams((1, 2, 44100, len(data), 'NONE', 'not compressed'))
        for sample in data:
            w.writeframes(struct.pack('h', int(sample * 32767.0)))
    print(f"Generated: {filename}")

def generate_pulse_wave(freq, duration_sec, volume=0.5, duty=0.25):
    # Simulates NES/Gameboy pulse wave with duty cycle
    sample_rate = 44100
    n_samples = int(sample_rate * duration_sec)
    data = []
    for i in range(n_samples):
        t = float(i) / sample_rate
        phase = (t * freq) % 1.0
        value = 1.0 if phase < duty else -1.0
        data.append(value * volume)
    return data

# GAMEBOY STYLE ROTATE
# A short, tonal pulse. Not a slide, not a click.
# ~0.05s, slightly higher pitch
rotate_sound = generate_pulse_wave(600, 0.05, 0.2, duty=0.5) 
save_wav("rotate.wav", rotate_sound)
