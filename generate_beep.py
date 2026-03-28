import wave
import struct
import math
import os

def create_beep(filename, duration=0.1, freq=1000.0, volume=0.5):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    sample_rate = 44100
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1) # mono
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            # smooth envelope to avoid clicking
            envelope = 1.0
            if i < 400: envelope = i / 400.0
            elif i > num_samples - 400: envelope = (num_samples - i) / 400.0
                
            value = int(volume * envelope * 32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

create_beep('c:/KioskVision/static/assets/beep.wav', duration=0.1, freq=1000.0)
create_beep('c:/KioskVision/static/assets/success.wav', duration=0.2, freq=2000.0)
create_beep('c:/KioskVision/static/assets/tick.wav', duration=0.03, freq=1200.0, volume=0.3)
print("Sounds created!")
