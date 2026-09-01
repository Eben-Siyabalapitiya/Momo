#!/bin/bash
while true; do
    arecord -D plughw:0,0 -f S16_LE -r 16000 -c 1 -d 4 /tmp/loud_raw.wav
    sox /tmp/loud_raw.wav -v 8.0 /tmp/loud_out.wav
    aplay -D plughw:0,0 /tmp/loud_out.wav
done
