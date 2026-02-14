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

def generate_square_wave(freq, duration_sec, volume=0.5):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_sec)
    data = []
    for i in range(n_samples):
        t = float(i) / sample_rate
        value = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        data.append(value * volume)
    return data

# New clean rotate sound
# A quick double-blip: High -> slightly Lower
# This gives a satisfying "mechanical" feel
part1 = generate_square_wave(800, 0.03, 0.15)
part2 = generate_square_wave(600, 0.03, 0.15)
save_wav("rotate.wav", part1 + part2)
