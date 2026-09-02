import json
import os
import subprocess
import tempfile
import requests
import speech_recognition as sr
from dotenv import load_dotenv
import face

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_KEY}"

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
MAX_HISTORY = 8

VALID_FACES = {
    "neutral", "happy", "sad", "annoyed", "confused",
    "sleepy", "excited", "curious", "smug"
}

SYSTEM_PROMPT = """You are Momo, a small four-legged robot spider. You are curious, a bit dramatic, and fond of your owner. You know you cannot climb walls. Keep replies under 15 words.

Respond with ONLY raw JSON, no markdown, no code fences, in exactly this shape:
{"say": "your reply here", "face": "one of neutral, happy, sad, annoyed, confused, sleepy, excited, curious, smug", "remember": "a short fact worth remembering long term, or null if nothing new"}

Only fill "remember" when the owner shares something worth keeping, like their name, a preference, or a detail about their life or this build. Otherwise leave it null. Keep facts short, one sentence.
"""

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
    convo = SYSTEM_PROMPT + "\n\n"
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
        data = {"say": "I got a bit tangled in my own thoughts.", "face": "confused", "remember": None}

    say = data.get("say", "...")
    face_name = data.get("face", "neutral")
    if face_name not in VALID_FACES:
        face_name = "neutral"
    remember = data.get("remember")

    return say, face_name, remember


def speak(text):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as raw_file:
        raw_path = raw_file.name

    subprocess.run(["espeak", "-v", "en+f3", "-p", "68", "-s", "155", "-a", "140", "-w", raw_path, text])
    face.start_talking()
    subprocess.run(["aplay", "-D", "plughw:0,0", raw_path])
    face.stop_talking()

    os.remove(raw_path)


def handle_turn(text):
    say, face_name, remember = ask_gemini(text)
    face.set_current(face_name)
    speak(say)
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
