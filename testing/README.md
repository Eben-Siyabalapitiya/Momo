These are the quick scripts I used while building Momo to test parts one at a time before putting the whole thing together. None of these run automatically, they were just for checking hardware worked before writing the real code.

- `test_screen.py` - basic test for the little TFT screen, just cycles through some colors and prints "MOMO" on it. Used this to make sure the screen wiring and driver were working before writing the actual eye animation code.
- `test_servo.py` - moves one servo back and forth. Used this to check the servo driver board was wired right before building out the full leg control code.
- `mic_test_loop.sh` - plays a beep, records from the mic, plays it back louder, and loops. Used this to check the mic was actually picking up sound.
- `loud_loop.sh` - records audio and plays it back boosted in a loop. Used this while debugging the mic and speaker sharing the same wiring.

If you're setting this up yourself, run these first to make sure your hardware is wired correctly before touching the main code.
