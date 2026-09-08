import time
import face

face.init()
face.start_idle()

DOT_STATES = [".", "..", "..."]
i = 0
while True:
    face.show_overlay(["Waking up", DOT_STATES[i % len(DOT_STATES)]], duration=1.0)
    i += 1
    time.sleep(0.5)
