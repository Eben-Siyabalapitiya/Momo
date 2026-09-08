# Momo

Momo is a four legged robot spider I built from scratch, running on a Raspberry Pi Zero W. It has a little screen for a face, it walks, and you can actually talk to it. It listens to you, sends what you said to Google's Gemini AI, and replies out loud with a personality I wrote for it, plus it can wave, walk, sit, dance, and pose for pictures.

I started this as a personal project to learn about robotics, wiring, and building something that actually works end to end instead of just following a tutorial. Everything here was built piece by piece: WiFi, servos, the screen, the mic and speaker, then the AI on top.

## What it can do

- Talks back when you speak to it, using Gemini for the actual replies and espeak for the voice
- Has an animated face on a small screen instead of a plain readout, eyes that blink and look around on their own when idle
- Walks forward and backward, turns, sits, waves, dances, and holds poses for photos
- Has a web control panel you can open from your phone or laptop to control it manually, watch the live conversation, tweak its personality, or set up WiFi
- If it can't find a known WiFi network, it makes its own hotspot so you can connect and give it a new one, useful if you bring it somewhere else
- Remembers things you tell it between conversations

## Hardware

- Raspberry Pi Zero W
- PCA9685 servo driver board, controlling 8 MG90S servos (2 per leg)
- ST7735 1.8 inch SPI screen for the face
- I2S mic and amp/speaker combo
- Everything powered off a battery through a couple of UBECs

## How the code is laid out

Everything you actually need to build and run Momo lives in `core/`. Everything else in the repo is either testing scripts or deployment config, not code the robot needs to function.

- `core/voice.py` is the main program, it listens for speech, sends it to Gemini, gets a reply back, and speaks it while triggering whatever face or movement fits
- `core/web.py` runs the Flask web control panel
- `core/face.py` draws and animates the eyes on the screen
- `core/gait.py` has all the walking, turning, waving, sitting, and posing logic
- `core/servos.py` is the low level code that actually talks to the servo board
- `core/persona.py` holds Momo's personality and how it's told to respond, editable live from the web panel
- `core/voice_settings.py` stores the voice volume, speed, and pitch settings
- `core/wifi_setup.py` and `core/wifi_boot_check.py` handle the WiFi hotspot fallback
- `core/boot_splash.py` shows a "waking up" animation on the screen while everything else is starting
- `systemd/` has the service files that make everything start automatically when the Pi boots
- `testing/` has the small scripts I used to test individual hardware pieces (screen, servos, mic) before writing the real code, see the README in there for details

## Setup

This isn't really plug and play since it depends on my exact wiring, but if you're working from similar hardware, the systemd service files in `systemd/` show how everything is set up to run automatically, and the code itself is fairly straightforward to follow. You'll need your own Gemini API key in a `.env` file.

On the actual Pi, the files inside `core/` all sit together in one flat folder rather than a subfolder, since they look for each other and for their saved data (memory, settings, calibration) right next to themselves. If you're setting this up yourself, just keep everything from `core/` together in whatever folder you point the systemd services at.

## License

MIT, see LICENSE.
