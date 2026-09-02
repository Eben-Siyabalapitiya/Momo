import json
import os
import subprocess
import tempfile
import time
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

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
MAX_HISTORY = 8

VALID_FACES = {
    "neutral", "happy", "sad", "annoyed", "confused",
    "sleepy", "excited", "curious", "smug",
    "surprised", "playful", "bored", "shy", "dreamy", "alert"
}

VALID_ACTIONS = {"none", "wave", "walk", "turn_left", "turn_right"}

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


def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, phrase_time_limit=8)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None


def ask_gemini(text):
    convo = persona.load() + "\n\n"
    if facts:
        convo += "Things you already know about your owner:\n"
        for fact in facts:
            convo += f"- {fact}\n"
        convo += "\n"
    for turn in history[-MAX_HISTORY:]:
        convo += f"User: {turn['user']}\nMomo: {turn['momo']}\n"
    convo += f"User: {text}\nMomo:"

    body = {"contents": [{"parts": [{"text": convo}]}]}
    try:
        response = requests.post(GEMINI_URL, json=body, timeout=15)
        response.raise_for_status()
        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError):
        data = {"say": "I got a bit tangled in my own thoughts.", "face": "confused", "action": "none", "remember": None}

    say = data.get("say", "...")
    face_name = data.get("face", "neutral")
    if face_name not in VALID_FACES:
        face_name = "neutral"
    action = data.get("action", "none")
    if action not in VALID_ACTIONS:
        action = "none"
    remember = data.get("remember")

    return say, face_name, action, remember


def speak(text):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as raw_file:
        raw_path = raw_file.name

    settings = voice_settings.load()
    subprocess.run([
        "espeak", "-v", "en+m7",
        "-p", str(settings["pitch"]),
        "-s", str(settings["speed"]),
        "-a", str(settings["amplitude"]),
        "-w", raw_path, text
    ])
    face.start_talking()
    try:
        amp_enable.value = True
        time.sleep(0.03)
        subprocess.run(["aplay", "-D", "plughw:0,0", "--buffer-time=500000", raw_path])
    finally:
        amp_enable.value = False
        face.stop_talking()
        os.remove(raw_path)


def perform_action(action):
    try:
        if action == "wave":
            gait.wave()
        elif action == "walk":
            gait.walk_trot(1)
        elif action == "turn_left":
            gait.turn_left_old(1)
        elif action == "turn_right":
            gait.turn_right_old(1)
    except Exception:
        pass


def handle_turn(text):
    say, face_name, action, remember = ask_gemini(text)
    face.set_current(face_name)
    speak(say)
    perform_action(action)
    history.append({"user": text, "momo": say})
    if len(history) > MAX_HISTORY:
        del history[0]
    if remember:
        facts.append(remember)
        save_memory()
    return say, face_name


def run():
    load_memory()
    face.init()
    face.set_current("curious")
    face.start_idle()
    try:
        while True:
            text = listen()
            if not text:
                continue
            print("heard:", text)
            say, face_name = handle_turn(text)
            print("momo:", say, "|", face_name)
    except KeyboardInterrupt:
        pass
    finally:
        save_memory()


if __name__ == "__main__":
    run()
