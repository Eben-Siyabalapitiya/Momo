import datetime
import json
import os
import random
import subprocess
import tempfile
import threading
import time
import numpy
import requests
import speech_recognition as sr
import board
import digitalio
from dotenv import load_dotenv
import face
import gait
import voice_settings
import persona

amp_enable = digitalio.DigitalInOut(board.D26)
amp_enable.direction = digitalio.Direction.OUTPUT
amp_enable.value = False

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_KEY}"

session = requests.Session()

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
TRANSCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcript.json")
CHAT_INBOX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_inbox.json")
MAX_HISTORY = 8

turn_lock = threading.Lock()

VALID_FACES = {
    "neutral", "happy", "sad", "annoyed", "confused",
    "sleepy", "excited", "curious", "smug",
    "surprised", "playful", "bored", "shy", "dreamy", "alert",
    "determined", "sneaky", "proud", "worried", "silly"
}

VALID_ACTIONS = {"none", "wave", "walk", "walk_back", "turn_left", "turn_right", "dance", "sit", "stand"}

TIME_KEYWORDS = {"time", "clock"}
WEATHER_KEYWORDS = {"weather", "forecast", "temperature", "raining", "outside"}

EMPTY_REPLY_FALLBACKS = [
    "nah, too lazy for that one.",
    "my brain just blanked, say that again?",
    "not sure how to answer that, try me again.",
    "eh, can't do that one.",
]

WAKEUP_GREETINGS = [
    "finally awake, hey!",
    "systems online, let's go.",
    "okay I'm up, what's good.",
    "booted and ready, hit me.",
    "back online, miss me?",
    "awake and annoyed about it, what's up.",
    "alive again, barely.",
]

history = []
facts = []


def load_memory():
    global history, facts
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH) as f:
            data = json.load(f)
        history = data.get("history", [])
        facts = data.get("facts", [])


def save_memory():
    with open(MEMORY_PATH, "w") as f:
        json.dump({"history": history, "facts": facts}, f, indent=2)


def save_transcript():
    try:
        with open(TRANSCRIPT_PATH, "w") as f:
            json.dump(history, f, indent=2)
    except OSError:
        pass


recognizer = sr.Recognizer()


def calibrate_mic():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.0)


MIC_GAIN = 5.0


def _boost_audio(audio, gain=MIC_GAIN):
    raw = audio.get_raw_data()
    samples = numpy.frombuffer(raw, dtype=numpy.int16).astype(numpy.float32)
    boosted = numpy.clip(samples * gain, -32768, 32767).astype(numpy.int16)
    return sr.AudioData(boosted.tobytes(), audio.sample_rate, audio.sample_width)


def listen():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            print("stt: no speech detected")
            return None
    audio = _boost_audio(audio)
    stt_start = time.time()
    try:
        text = recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        text = None
        print("stt: could not understand audio")
    except sr.RequestError as e:
        text = None
        print(f"stt: request error: {e}")
    print(f"timing: stt={time.time() - stt_start:.2f}s")
    return text


def get_weather():
    try:
        response = session.get("https://wttr.in/?format=%C+%t", timeout=6)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException:
        return None


def ask_gemini(text, extra=None):
    convo = persona.load() + "\n\n"
    if extra:
        convo += extra + "\n\n"
    if facts:
        convo += "Things you already know about your owner:\n"
        for fact in facts:
            convo += f"- {fact}\n"
        convo += "\n"
    for turn in history[-MAX_HISTORY:]:
        convo += f"User: {turn['user']}\nMomo: {turn['momo']}\n"
    convo += f"User: {text}\nMomo:"

    body = {"contents": [{"parts": [{"text": convo}]}]}
    gemini_start = time.time()
    try:
        response = session.post(GEMINI_URL, json=body, timeout=15)
        print(f"timing: gemini={time.time() - gemini_start:.2f}s")
        response.raise_for_status()
        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError):
        data = {"say": "I got a bit tangled in my own thoughts.", "face": "confused", "actions": [], "show": None, "remember": None}

    say = data.get("say") or ""
    say = say.strip()
    if not say:
        say = random.choice(EMPTY_REPLY_FALLBACKS)
    face_name = data.get("face", "neutral")
    if face_name not in VALID_FACES:
        face_name = "neutral"

    raw_actions = data.get("actions", data.get("action", []))
    if isinstance(raw_actions, str):
        raw_actions = [raw_actions]
    actions = [a for a in raw_actions if a in VALID_ACTIONS and a != "none"]

    show = data.get("show") or None
    if show:
        show = str(show).strip() or None

    remember = data.get("remember")

    return say, face_name, actions, show, remember


def speak(text):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as raw_file:
        raw_path = raw_file.name

    settings = voice_settings.load()
    synth_start = time.time()
    subprocess.run([
        "espeak", "-v", "en+m7",
        "-p", str(settings["pitch"]),
        "-s", str(settings["speed"]),
        "-a", str(settings["amplitude"]),
        "-w", raw_path, text
    ])
    print(f"timing: tts_synth={time.time() - synth_start:.2f}s")
    face.start_talking()
    try:
        amp_enable.value = True
        time.sleep(0.03)
        playback_start = time.time()
        subprocess.run(["aplay", "-D", "plughw:0,0", "--buffer-time=500000", raw_path])
        print(f"timing: tts_playback={time.time() - playback_start:.2f}s")
    finally:
        amp_enable.value = False
        face.stop_talking()
        os.remove(raw_path)


def _run_one_action(action):
    if action == "wave":
        gait.wave()
    elif action == "walk":
        gait.walk_trot(1)
    elif action == "walk_back":
        gait.walk_backward(1)
    elif action == "turn_left":
        gait.turn_left_old(1)
    elif action == "turn_right":
        gait.turn_right_old(1)
    elif action == "dance":
        face.party_flash(gait.DANCE_REPS * gait.DANCE_STEP_DELAY * 2 + 0.5)
        gait.dance()
    elif action == "sit":
        gait.sit()
    elif action == "stand":
        gait.stand()


def perform_actions(actions):
    for action in actions:
        try:
            _run_one_action(action)
        except Exception:
            pass


def handle_turn(text):
    turn_start = time.time()
    lowered = text.lower()
    extra = None
    overlay = None
    if any(k in lowered for k in TIME_KEYWORDS):
        now_str = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
        extra = f"The current time is {now_str}."
        overlay = ["Time", now_str]
    elif any(k in lowered for k in WEATHER_KEYWORDS):
        weather = get_weather()
        if weather:
            extra = f"The current weather is: {weather}."
            overlay = ["Weather", weather]

    say, face_name, actions, show, remember = ask_gemini(text, extra)
    face.set_current(face_name)
    action_thread = threading.Thread(target=perform_actions, args=(actions,), daemon=True)
    action_thread.start()
    speak(say)
    display = overlay or ([show] if show else None)
    if display:
        face.show_overlay(display, duration=6.0)
    action_thread.join()
    history.append({"user": text, "momo": say})
    if len(history) > MAX_HISTORY:
        del history[0]
    save_transcript()
    if remember:
        facts.append(remember)
        save_memory()
    print(f"timing: turn_total={time.time() - turn_start:.2f}s")
    return say, face_name


def chat_inbox_loop():
    last_id = None
    while True:
        time.sleep(1)
        try:
            with open(CHAT_INBOX_PATH) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if data.get("id") == last_id:
            continue
        last_id = data.get("id")
        text = (data.get("text") or "").strip()
        if not text:
            continue
        with turn_lock:
            print("typed:", text)
            say, face_name = handle_turn(text)
            print("momo:", say, "|", face_name)


def run():
    load_memory()
    face.init()
    face.set_current("curious")
    face.start_idle()
    calibrate_mic()
    face.set_current("excited")
    greeting = random.choice(WAKEUP_GREETINGS)
    print("greeting:", greeting)
    speak(greeting)
    face.set_current("curious")
    threading.Thread(target=chat_inbox_loop, daemon=True).start()
    try:
        while True:
            text = listen()
            if not text:
                continue
            with turn_lock:
                print("heard:", text)
                say, face_name = handle_turn(text)
                print("momo:", say, "|", face_name)
    except KeyboardInterrupt:
        pass
    finally:
        save_memory()


if __name__ == "__main__":
    run()
