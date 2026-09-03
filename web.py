import threading
import subprocess
import time
import board
import digitalio
from flask import Flask, request, render_template_string, jsonify
import servos
import gait
import voice_settings
import persona
import wifi_setup

app = Flask(__name__)
gait_lock = threading.Lock()

amp_enable = digitalio.DigitalInOut(board.D26)
amp_enable.direction = digitalio.Direction.OUTPUT
amp_enable.value = False

PAGE = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Momo</title>
<style>
  :root {
    --bg: #0c0e12;
    --panel: #14171d;
    --panel-2: #1a1e25;
    --border: #23272f;
    --text: #e7e6e2;
    --muted: #8b8f98;
    --accent: #4fc9be;
    --accent-dim: rgba(79, 201, 190, 0.12);
    --danger: #c0506a;
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--text); margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .shell { max-width: 640px; margin: 0 auto; padding: 2rem 1.4rem 4rem; }
  .brand { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.6rem; }
  .brand .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent);
                box-shadow: 0 0 10px var(--accent); }
  .brand h1 { font-size: 1.1rem; font-weight: 600; margin: 0; letter-spacing: 0.01em; }

  nav.tabs { display: flex; gap: 0.4rem; margin-bottom: 1.8rem;
             background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 0.3rem; }
  nav.tabs button { flex: 1; background: transparent; border: none; color: var(--muted);
                     font-size: 0.88rem; font-weight: 500; padding: 0.55rem 0.4rem; border-radius: 9px;
                     cursor: pointer; transition: background 0.15s, color 0.15s; }
  nav.tabs button.active { background: var(--accent-dim); color: var(--accent); }

  section { display: none; }
  section.active { display: block; }

  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
          padding: 1.2rem 1.3rem; margin-bottom: 1rem; }
  .card h2 { font-size: 0.95rem; font-weight: 600; margin: 0 0 0.2rem; }
  .card .sub { font-size: 0.8rem; color: var(--muted); margin: 0 0 1rem; }

  .actions { display: flex; gap: 0.6rem; flex-wrap: wrap; }
  button.btn { background: var(--panel-2); color: var(--text); border: 1px solid var(--border);
               border-radius: 10px; padding: 0.65rem 1.1rem; font-size: 0.88rem; font-weight: 500;
               cursor: pointer; transition: border-color 0.15s, opacity 0.15s; }
  button.btn:hover { border-color: var(--accent); }
  button.btn:disabled { opacity: 0.4; cursor: default; }
  button.btn:disabled:hover { border-color: var(--border); }
  button.btn.primary { background: var(--accent); color: #06110f; border: none; }
  button.btn.danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); }

  .dpad { display: grid; grid-template-columns: repeat(3, 4.4rem); grid-template-rows: repeat(3, 4.4rem);
          gap: 0.5rem; justify-content: center; margin: 0.4rem auto 0; }
  .dpad-btn { background: var(--panel-2); border: 1px solid var(--border); border-radius: 16px;
              color: var(--text); font-size: 1.3rem; display: flex; align-items: center; justify-content: center;
              cursor: pointer; transition: border-color 0.15s, background 0.15s; }
  .dpad-btn:active { background: var(--accent-dim); border-color: var(--accent); }
  .dpad-up { grid-column: 2; grid-row: 1; }
  .dpad-left { grid-column: 1; grid-row: 2; }
  .dpad-center { grid-column: 2; grid-row: 2; font-size: 0.7rem; font-weight: 600;
                 background: var(--accent-dim); color: var(--accent); border-color: var(--accent); }
  .dpad-right { grid-column: 3; grid-row: 2; }
  .dpad-down { grid-column: 2; grid-row: 3; }

  .row { display: flex; align-items: center; gap: 0.8rem; }
  .row label { width: 5.5rem; font-size: 0.85rem; color: var(--muted); }
  input[type=range] { flex: 1; accent-color: var(--accent); }
  .val { width: 2.6rem; text-align: right; font-variant-numeric: tabular-nums; font-size: 0.85rem; }

  textarea.persona {
    width: 100%; min-height: 220px; background: var(--panel-2); color: var(--text);
    border: 1px solid var(--border); border-radius: 10px; padding: 0.9rem; font-size: 0.85rem;
    line-height: 1.5; resize: vertical; font-family: inherit;
  }
  .save-row { display: flex; align-items: center; gap: 0.8rem; margin-top: 0.8rem; }
  .saved-flag { font-size: 0.8rem; color: var(--accent); opacity: 0; transition: opacity 0.2s; }
  .saved-flag.show { opacity: 1; }

  .leg-group { margin-bottom: 0.7rem; }
  .leg-group:last-child { margin-bottom: 0; }
  .leg-group h3 { font-size: 0.72rem; color: var(--muted); text-transform: uppercase;
                  letter-spacing: 0.06em; margin: 0 0 0.4rem; font-weight: 600; }
  .channel { margin-bottom: 0.7rem; }
  .channel:last-child { margin-bottom: 0; }
  .startup { font-size: 0.72rem; color: var(--muted); margin: 0.3rem 0 0.5rem; font-variant-numeric: tabular-nums; }
  .btns { display: flex; gap: 0.4rem; }
  .btns button { flex: 1; padding: 0.4rem; font-size: 0.78rem; }
  .divider { border: none; border-top: 1px solid var(--border); margin: 1.4rem 0; }
</style>
</head>
<body>
<div class="shell">
  <div class="brand"><span class="dot"></span><h1>Momo</h1></div>

  <nav class="tabs">
    <button class="tab-btn active" data-tab="control">Control</button>
    <button class="tab-btn" data-tab="personality">Personality</button>
    <button class="tab-btn" data-tab="wifi">WiFi</button>
    <button class="tab-btn" data-tab="calibration">Calibration</button>
  </nav>

  <section id="tab-control" class="active">
    <div class="card">
      <h2>Move</h2>
      <p class="sub">Each press runs 2 step cycles.</p>
      <div class="dpad">
        <button class="dpad-btn dpad-up" id="dpadUp" onclick="move('forward')">&#9650;</button>
        <button class="dpad-btn dpad-left" id="dpadLeft" onclick="move('left')">&#9664;</button>
        <button class="dpad-btn dpad-center" onclick="goHome()">Home</button>
        <button class="dpad-btn dpad-right" id="dpadRight" onclick="move('right')">&#9654;</button>
        <button class="dpad-btn dpad-down" id="dpadDown" onclick="move('backward')">&#9660;</button>
      </div>
      <div class="actions" style="margin-top:1.1rem;">
        <button class="btn" id="waveBtn" onclick="wave()">Wave</button>
        <button class="btn" id="sitBtn" onclick="sit()">Sit</button>
        <button class="btn" id="danceBtn" onclick="dance()">Dance</button>
      </div>
    </div>

    <div class="card">
      <h2>Voice</h2>
      <p class="sub">Adjust and press Save to apply on Momo immediately. No restart needed.</p>
      <div class="row">
        <label>Volume</label>
        <input type="range" min="0" max="200" value="{{ volume }}" id="volumeSlider" oninput="onVolume(this.value)">
        <span class="val" id="volumeVal">{{ volume }}</span>
      </div>
      <div class="row" style="margin-top:0.6rem;">
        <label>Speed</label>
        <input type="range" min="80" max="250" value="{{ speed }}" id="speedSlider" oninput="onSpeed(this.value)">
        <span class="val" id="speedVal">{{ speed }}</span>
      </div>
      <div class="save-row">
        <button class="btn primary" onclick="saveVoiceSettings()">Save</button>
        <span class="saved-flag" id="volumeSavedFlag">Saved</span>
      </div>
      <div class="actions" style="margin-top:0.9rem;">
        <button class="btn" onclick="testVoice()">Test Voice</button>
      </div>
    </div>

    <div class="card">
      <h2>Testing</h2>
      <p class="sub">Newer paired turning, for comparison against the one-leg-at-a-time version used above.</p>
      <div class="actions">
        <button class="btn" id="turnLeftNewBtn" onclick="turnNew('left')">Turn Left (New)</button>
        <button class="btn" id="turnRightNewBtn" onclick="turnNew('right')">Turn Right (New)</button>
      </div>
    </div>
  </section>

  <section id="tab-personality">
    <div class="card">
      <h2>System Prompt</h2>
      <p class="sub">This is sent to Gemini before every message. Change how Momo thinks and talks here.</p>
      <textarea class="persona" id="personaText">{{ persona_prompt }}</textarea>
      <div class="save-row">
        <button class="btn primary" onclick="savePersona()">Save</button>
        <span class="saved-flag" id="savedFlag">Saved</span>
      </div>
    </div>
  </section>

  <section id="tab-wifi">
    <div class="card">
      <h2>Status</h2>
      <p class="sub" id="wifiStatusText">Checking...</p>
      <div class="actions">
        <button class="btn" onclick="refreshWifiStatus()">Refresh</button>
      </div>
    </div>

    <div class="card">
      <h2>Connect to a Network</h2>
      <p class="sub">Scan for nearby networks, or type a name directly.</p>
      <div class="actions" style="margin-bottom:0.9rem;">
        <button class="btn" onclick="scanWifi()" id="scanBtn">Scan Networks</button>
      </div>
      <div id="wifiList"></div>
      <div class="row" style="margin-top:0.9rem;">
        <label>Network</label>
        <input type="text" id="wifiSsid" placeholder="Network name"
               style="flex:1;background:var(--panel-2);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:0.5rem 0.7rem;">
      </div>
      <div class="row" style="margin-top:0.6rem;">
        <label>Password</label>
        <input type="password" id="wifiPassword" placeholder="Password"
               style="flex:1;background:var(--panel-2);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:0.5rem 0.7rem;">
      </div>
      <div class="actions" style="margin-top:0.9rem;">
        <button class="btn primary" onclick="connectWifi()" id="connectBtn">Connect</button>
      </div>
      <p class="sub" id="wifiConnectStatus" style="margin-top:0.8rem;"></p>
    </div>
  </section>

  <section id="tab-calibration">
    <div class="card">
      <h2>All Driver Servos</h2>
      <div class="row">
        <input type="range" min="0" max="180" value="90" id="group_all_main"
               oninput="groupSlide([0,2,4,6], this.value, 'group_all_main_val')">
        <span class="val" id="group_all_main_val">90</span>
      </div>
    </div>

    {% for group in groups %}
    <div class="card">
      <h2>{{ group.side }}</h2>
      <div class="leg-group">
        <h3>Main Servos</h3>
        <div class="row">
          <input type="range" min="0" max="180" value="90" id="group_{{ group.id }}_main"
                 oninput="groupSlide([{{ group.main|join(',') }}], this.value, 'group_{{ group.id }}_main_val')">
          <span class="val" id="group_{{ group.id }}_main_val">90</span>
        </div>
      </div>
      <div class="leg-group">
        <h3>Joint Servos</h3>
        <div class="row">
          <input type="range" min="0" max="180" value="90" id="group_{{ group.id }}_joint"
                 oninput="groupSlide([{{ group.joint|join(',') }}], this.value, 'group_{{ group.id }}_joint_val')">
          <span class="val" id="group_{{ group.id }}_joint_val">90</span>
        </div>
      </div>
    </div>
    {% endfor %}

    <div class="card">
      <h2>Per-Leg Calibration</h2>
      <div class="actions" style="margin-bottom:1.2rem;">
        <button class="btn primary" onclick="assembleAll()">Assemble Pose</button>
        <button class="btn primary" onclick="saveAllStartup()">Save All as Startup</button>
        <button class="btn danger" onclick="allRelease()">Release All</button>
        <button class="btn danger" onclick="resetAll()">Reset All</button>
      </div>

      {% for leg in legs %}
      <h3 style="font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;margin:1rem 0 0.5rem;font-weight:600;">{{ leg.name }}</h3>
      {% for joint in [("Hip", leg.hip), ("Knee", leg.knee)] %}
      <div class="channel">
        <div class="row">
          <label>{{ joint[0] }}</label>
          <input type="range" min="0" max="180" value="{{ startups[joint[1]|string] }}" id="slider{{ joint[1] }}"
                 oninput="onSlide({{ joint[1] }}, this.value)">
          <span class="val" id="val{{ joint[1] }}">{{ startups[joint[1]|string] }}</span>
        </div>
        <div class="startup" id="startup{{ joint[1] }}">startup: {{ startups[joint[1]|string] }}&deg;</div>
        <div class="btns">
          <button class="btn" onclick="jump({{ joint[1] }}, 90)">90&deg;</button>
          <button class="btn" onclick="jump({{ joint[1] }}, 180)">180&deg;</button>
          <button class="btn" onclick="release({{ joint[1] }})">Release</button>
          <button class="btn primary" onclick="saveStartup({{ joint[1] }})">Save</button>
        </div>
      </div>
      {% endfor %}
      {% endfor %}
    </div>
  </section>
</div>

<script>
document.querySelectorAll(".tab-btn").forEach(function(btn) {
  btn.addEventListener("click", function() {
    document.querySelectorAll(".tab-btn").forEach(function(b) { b.classList.remove("active"); });
    document.querySelectorAll("section").forEach(function(s) { s.classList.remove("active"); });
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "wifi") refreshWifiStatus();
  });
});

async function post(url, body) {
  await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body || {})
  });
}

const THROTTLE_MS = 60;
let lastSend = {};

function throttled(key, fn) {
  const now = Date.now();
  if (now - (lastSend[key] || 0) < THROTTLE_MS) return;
  lastSend[key] = now;
  fn();
}

function onSlide(ch, angle) {
  document.getElementById("val" + ch).textContent = angle;
  throttled("ch" + ch, function() {
    post("/set", {channel: ch, angle: parseInt(angle)});
  });
}

function jump(ch, angle) {
  document.getElementById("slider" + ch).value = angle;
  document.getElementById("val" + ch).textContent = angle;
  post("/set", {channel: ch, angle: angle});
}

function groupSlide(channels, angle, valId) {
  document.getElementById(valId).textContent = angle;
  channels.forEach(function(ch) {
    document.getElementById("slider" + ch).value = angle;
    document.getElementById("val" + ch).textContent = angle;
  });
  throttled("group" + channels.join("-"), function() {
    post("/set_multi", {
      channels: channels.map(function(ch) { return {channel: ch, angle: parseInt(angle)}; })
    });
  });
}

function release(ch) {
  post("/release", {channel: ch});
}

async function saveStartup(ch) {
  const angle = parseInt(document.getElementById("slider" + ch).value);
  const res = await fetch("/save_startup", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({channel: ch, angle: angle})
  });
  const data = await res.json();
  document.getElementById("startup" + ch).textContent = "startup: " + data.startup + "°";
}

function assembleAll() {
  for (let ch = 0; ch < 8; ch++) {
    const text = document.getElementById("startup" + ch).textContent;
    const angle = parseInt(text.replace(/[^0-9]/g, ""));
    jump(ch, angle);
  }
}

async function saveAllStartup() {
  for (let ch = 0; ch < 8; ch++) {
    await saveStartup(ch);
  }
}

function allRelease() {
  for (let ch = 0; ch < 8; ch++) release(ch);
}

const MOVE_ROUTES = {forward: "/walk", backward: "/walk_back", left: "/turn_left_old", right: "/turn_right_old"};
const MOVE_BTNS = {forward: "dpadUp", backward: "dpadDown", left: "dpadLeft", right: "dpadRight"};

async function move(dir) {
  const btn = document.getElementById(MOVE_BTNS[dir]);
  btn.disabled = true;
  await post(MOVE_ROUTES[dir], {});
  btn.disabled = false;
}

function goHome() {
  post("/home", {});
}

async function turnNew(dir) {
  const btn = document.getElementById(dir === "left" ? "turnLeftNewBtn" : "turnRightNewBtn");
  btn.disabled = true;
  btn.textContent = "Turning...";
  await post("/turn_" + dir, {});
  btn.disabled = false;
  btn.textContent = dir === "left" ? "Turn Left (New)" : "Turn Right (New)";
}

async function wave() {
  const btn = document.getElementById("waveBtn");
  btn.disabled = true;
  btn.textContent = "Waving...";
  await post("/wave", {});
  btn.disabled = false;
  btn.textContent = "Wave";
}

async function sit() {
  const btn = document.getElementById("sitBtn");
  btn.disabled = true;
  await post("/sit", {});
  btn.disabled = false;
}

async function dance() {
  const btn = document.getElementById("danceBtn");
  btn.disabled = true;
  btn.textContent = "Dancing...";
  await post("/dance", {});
  btn.disabled = false;
  btn.textContent = "Dance";
}

function onVolume(value) {
  document.getElementById("volumeVal").textContent = value;
}

function onSpeed(value) {
  document.getElementById("speedVal").textContent = value;
}

function currentVoiceSettings() {
  return {
    amplitude: parseInt(document.getElementById("volumeSlider").value),
    speed: parseInt(document.getElementById("speedSlider").value)
  };
}

async function saveVoiceSettings() {
  await post("/set_volume", currentVoiceSettings());
  const flag = document.getElementById("volumeSavedFlag");
  flag.classList.add("show");
  setTimeout(function() { flag.classList.remove("show"); }, 1600);
}

async function testVoice() {
  await post("/set_volume", currentVoiceSettings());
  post("/test_voice", {});
}

async function resetAll() {
  await post("/reset_all", {});
  for (let ch = 0; ch < 8; ch++) {
    document.getElementById("slider" + ch).value = 90;
    document.getElementById("val" + ch).textContent = 90;
    document.getElementById("startup" + ch).textContent = "startup: 90°";
  }
}

async function savePersona() {
  const prompt = document.getElementById("personaText").value;
  await post("/save_persona", {prompt: prompt});
  const flag = document.getElementById("savedFlag");
  flag.classList.add("show");
  setTimeout(function() { flag.classList.remove("show"); }, 1600);
}

async function refreshWifiStatus() {
  const el = document.getElementById("wifiStatusText");
  el.textContent = "Checking...";
  try {
    const res = await fetch("/wifi/status");
    const data = await res.json();
    if (data.mode === "connected") {
      el.textContent = "Connected to " + data.ssid + " (" + data.ip + ")";
    } else if (data.mode === "hotspot") {
      el.textContent = "Setup mode active — broadcasting its own WiFi for new-network setup.";
    } else {
      el.textContent = "Status unknown.";
    }
  } catch (e) {
    el.textContent = "Could not check status.";
  }
}

async function scanWifi() {
  const btn = document.getElementById("scanBtn");
  const listEl = document.getElementById("wifiList");
  btn.disabled = true;
  btn.textContent = "Scanning...";
  listEl.innerHTML = "";
  try {
    const res = await fetch("/wifi/scan", {method: "POST"});
    const networks = await res.json();
    networks.forEach(function(n) {
      const row = document.createElement("button");
      row.className = "btn";
      row.style.display = "block";
      row.style.width = "100%";
      row.style.textAlign = "left";
      row.style.marginBottom = "0.4rem";
      row.textContent = n.ssid + (n.secured ? " 🔒" : "") + "  ·  signal " + n.signal + "%";
      row.onclick = function() { document.getElementById("wifiSsid").value = n.ssid; };
      listEl.appendChild(row);
    });
  } finally {
    btn.disabled = false;
    btn.textContent = "Scan Networks";
  }
}

async function connectWifi() {
  const ssid = document.getElementById("wifiSsid").value.trim();
  const password = document.getElementById("wifiPassword").value;
  const statusEl = document.getElementById("wifiConnectStatus");
  const btn = document.getElementById("connectBtn");
  if (!ssid) {
    statusEl.textContent = "Type or pick a network name first.";
    return;
  }
  btn.disabled = true;
  statusEl.textContent = "Connecting to " + ssid + "... Momo's own hotspot will drop now — if it succeeds, join " + ssid + " with this device to keep using the panel.";
  try {
    await post("/wifi/connect", {ssid: ssid, password: password});
  } catch (e) {}
  btn.disabled = false;
}
</script>
</body>
</html>
"""


LEGS_ORDER = [
    {"name": "Front Right", "hip": 0, "knee": 1},
    {"name": "Back Right", "hip": 2, "knee": 3},
    {"name": "Front Left", "hip": 4, "knee": 5},
    {"name": "Back Left", "hip": 6, "knee": 7},
]

SIDE_GROUPS = [
    {"id": "right", "side": "Right Side", "main": [0, 2], "joint": [1, 3]},
    {"id": "left", "side": "Left Side", "main": [4, 6], "joint": [5, 7]},
]


@app.route("/")
def index():
    startups = {str(ch): servos.get_startup(ch) for ch in range(8)}
    settings = voice_settings.load()
    persona_prompt = persona.load()
    return render_template_string(
        PAGE, legs=LEGS_ORDER, groups=SIDE_GROUPS, startups=startups,
        volume=settings["amplitude"], speed=settings["speed"], persona_prompt=persona_prompt
    )


@app.route("/set", methods=["POST"])
def set_angle():
    data = request.get_json()
    servos.set_channel(int(data["channel"]), int(data["angle"]))
    return "", 204


@app.route("/set_multi", methods=["POST"])
def set_multi():
    data = request.get_json()
    for item in data["channels"]:
        servos.set_channel(int(item["channel"]), int(item["angle"]))
    return "", 204


@app.route("/release", methods=["POST"])
def release():
    data = request.get_json()
    servos.release_channel(int(data["channel"]))
    return "", 204


@app.route("/save_startup", methods=["POST"])
def save_startup():
    data = request.get_json()
    channel = int(data["channel"])
    angle = int(data["angle"])
    servos.save_startup(channel, angle)
    return {"startup": servos.get_startup(channel)}


@app.route("/reset_all", methods=["POST"])
def reset_all():
    servos.reset_all()
    return "", 204


@app.route("/set_volume", methods=["POST"])
def set_volume():
    data = request.get_json()
    settings = voice_settings.load()
    settings["amplitude"] = int(data["amplitude"])
    if "speed" in data:
        settings["speed"] = int(data["speed"])
    voice_settings.save(settings)
    return "", 204


@app.route("/test_voice", methods=["POST"])
def test_voice():
    settings = voice_settings.load()
    subprocess.run([
        "espeak", "-v", "en+m7",
        "-p", str(settings["pitch"]),
        "-s", str(settings["speed"]),
        "-a", str(settings["amplitude"]),
        "-w", "/tmp/web_voice_test.wav", "Hi, I'm Momo!"
    ])
    try:
        amp_enable.value = True
        time.sleep(0.03)
        subprocess.run(["aplay", "-D", "plughw:0,0", "--buffer-time=500000", "/tmp/web_voice_test.wav"])
    finally:
        amp_enable.value = False
    return "", 204


@app.route("/save_persona", methods=["POST"])
def save_persona():
    data = request.get_json()
    persona.save(data["prompt"])
    return "", 204


@app.route("/home", methods=["POST"])
def home():
    for ch in range(8):
        servos.set_channel(ch, servos.get_startup(ch))
    return "", 204


@app.route("/wifi/status")
def wifi_status():
    return jsonify(wifi_setup.read_status())


@app.route("/wifi/scan", methods=["POST"])
def wifi_scan():
    return jsonify(wifi_setup.scan_networks())


@app.route("/wifi/connect", methods=["POST"])
def wifi_connect():
    data = request.get_json()
    ssid = data.get("ssid", "").strip()
    password = data.get("password", "")
    if not ssid:
        return "", 400
    wifi_setup.write_status("connecting", ssid=ssid)
    wifi_setup.connect_async(ssid, password)
    return "", 202


@app.route("/wave", methods=["POST"])
def wave_route():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.wave()
    finally:
        gait_lock.release()
    return "", 204


@app.route("/sit", methods=["POST"])
def sit_route():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.sit()
    finally:
        gait_lock.release()
    return "", 204


@app.route("/dance", methods=["POST"])
def dance_route():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.dance()
    finally:
        gait_lock.release()
    return "", 204


@app.route("/turn_left", methods=["POST"])
def turn_left_route():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.turn_left()
    finally:
        gait_lock.release()
    return "", 204


@app.route("/turn_right", methods=["POST"])
def turn_right_route():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.turn_right()
    finally:
        gait_lock.release()
    return "", 204


@app.route("/turn_left_old", methods=["POST"])
def turn_left_old_route():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.turn_left_old()
    finally:
        gait_lock.release()
    return "", 204


@app.route("/turn_right_old", methods=["POST"])
def turn_right_old_route():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.turn_right_old()
    finally:
        gait_lock.release()
    return "", 204


@app.route("/walk", methods=["POST"])
def walk():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.walk_trot(2)
    finally:
        gait_lock.release()
    return "", 204


@app.route("/walk_back", methods=["POST"])
def walk_back():
    if not gait_lock.acquire(blocking=False):
        return "", 409
    try:
        gait.walk_backward(2)
    finally:
        gait_lock.release()
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
