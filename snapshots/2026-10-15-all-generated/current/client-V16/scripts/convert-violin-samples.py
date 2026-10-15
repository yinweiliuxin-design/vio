"""Reproducibly derive the seven approved CC0 violin assets; Python standard library only."""
import argparse
import hashlib
import json
import math
import pathlib
import struct
import wave

COMMIT = '440300901dfe9275fd84e0b7763af1f8443ae62e'
PITCHES = [('A3', 57), ('E4', 64), ('A4', 69), ('E5', 76), ('A5', 81), ('E6', 88), ('A6', 93)]
RATE, SECONDS = 22050, 2.8

def sha(data):
    return hashlib.sha256(data).hexdigest()

def convert(source, target):
    original = source.read_bytes()
    with wave.open(str(source), 'rb') as reader:
        if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) != (2, 2, 44100):
            raise ValueError('Expected pinned stereo PCM16 / 44100 Hz input: ' + source.name)
        raw = reader.readframes(reader.getnframes())
    stereo = struct.unpack('<' + 'h' * (len(raw) // 2), raw)
    mono = [(stereo[i] + stereo[i + 1]) / 65536 for i in range(0, len(stereo), 2)]
    peak = max(abs(value) for value in mono)
    if peak < .0001:
        raise ValueError('Source has no usable audio')
    onset = next(i for i, value in enumerate(mono) if abs(value) > peak * .006)
    # Keep a short pre-attack; downsample with a 63-tap windowed-sinc lowpass.
    start = max(0, onset - round(.010 * 44100))
    taps, cutoff = 63, .23
    kernel = []
    for index in range(taps):
        x = index - (taps - 1) / 2
        sinc = 2 * cutoff if x == 0 else math.sin(2 * math.pi * cutoff * x) / (math.pi * x)
        kernel.append(sinc * (.54 - .46 * math.cos(2 * math.pi * index / (taps - 1))))
    total = sum(kernel)
    kernel = [value / total for value in kernel]
    count = round(RATE * SECONDS)
    output = []
    for index in range(count):
        centre = start + index * 2
        output.append(sum(mono[position] * weight for offset, weight in enumerate(kernel)
                          if 0 <= (position := centre + offset - taps // 2) < len(mono)))
    normalizer = .80 / max(abs(value) for value in output)
    output = [value * normalizer for value in output]
    # Crossfade the end of the sustain region into the immediately preceding
    # segment of its start. At the boundary playback continues at loopStart.
    loop_start, loop_end, crossfade = round(.84 * RATE), round(2.6 * RATE), round(.04 * RATE)
    for index in range(crossfade):
        ratio = index / max(1, crossfade - 1)
        output[loop_end - crossfade + index] = (output[loop_end - crossfade + index] * (1-ratio)
                                                 + output[loop_start - crossfade + index] * ratio)
    attack, release = round(.003 * RATE), round(.020 * RATE)
    for index in range(attack):
        output[index] *= index / max(1, attack - 1)
    for index in range(release):
        output[-release + index] *= 1-index / max(1, release - 1)
    pcm = struct.pack('<' + 'h' * count, *(max(-32768, min(32767, round(value * 32767))) for value in output))
    with wave.open(str(target), 'wb') as writer:
        writer.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        writer.writeframes(pcm)
    return {'originalBytes': len(original), 'originalSha256': sha(original), 'bytes': target.stat().st_size,
            'sha256': sha(target.read_bytes()), 'frames': count, 'sampleRate': RATE, 'channels': 1,
            'bitsPerSample': 16, 'duration': count / RATE, 'loopStart': loop_start / RATE,
            'loopEnd': loop_end / RATE, 'sourceAttackOffsetSeconds': start / 44100}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent.parent / 'dist/assets/audio/violin')
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    samples = []
    for note, midi in PITCHES:
        name = 'LLVln_ArcoVib_' + note + '_p.wav'
        target = output / (note + '.wav')
        samples.append({'note': note, 'midi': midi, 'file': target.name, 'originalFile': name,
                        **convert(source / name, target)})
    if sum(item['bytes'] for item in samples) > 1000000:
        raise ValueError('Application WAV budget exceeded')
    license_bytes = (source / 'LICENSE.txt').read_bytes()
    if b'CC0' not in license_bytes:
        raise ValueError('Pinned CC0 license is missing')
    (output / 'LICENSE.txt').write_bytes(license_bytes)
    manifest = {'schema': 1, 'license': 'CC0-1.0', 'repository': 'https://github.com/sgossner/VSCO-2-CE',
                'commit': COMMIT, 'credits': 'Sam Gossner & Simon Dalzell; cutting: Elan Hickler/Soundemote',
                'description': 'Single-note arco vibrato samples, assembled by software; not a teacher performance or a tuning reference.',
                'conversion': 'Stereo mean; attack trim with 10ms pre-roll; 63-tap Hamming windowed-sinc 2:1 downsampling; peak 0.8; 40ms sustain crossfade; 3ms attack and 20ms tail fade; PCM16 mono 22050 Hz.',
                'licenseSha256': sha(license_bytes), 'totalWavBytes': sum(item['bytes'] for item in samples), 'samples': samples}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'samples': len(samples), 'wavBytes': manifest['totalWavBytes']}))

if __name__ == '__main__':
    main()
