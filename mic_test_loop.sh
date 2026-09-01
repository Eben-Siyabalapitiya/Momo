#!/bin/bash
sox -n /tmp/beep.wav synth 0.3 sine 800
while true; do
    aplay -D plughw:0,0 /tmp/beep.wav
    arecord -D plughw:0,0 -f S16_LE -r 16000 -c 1 -d 4 /tmp/mic_raw.wav
    sox /tmp/mic_raw.wav /tmp/mic_loud.wav gain 15
    aplay -D plughw:0,0 /tmp/mic_loud.wav
done
