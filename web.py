from flask import Flask, request, render_template_string
import servos

app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Momo Servo Panel</title>
<style>
  body { background:#12151a; color:#e8e6df; font-family:sans-serif; margin:0; padding:1.2rem; }
  h1 { font-size:1.3rem; margin:0 0 1rem; }
  .topbar { display:flex; gap:0.6rem; margin-bottom:1.4rem; flex-wrap:wrap; }
  button { background:#2a2f36; color:#e8e6df; border:1px solid #444; border-radius:8px;
           padding:0.6rem 1rem; font-size:0.95rem; }
  button.primary { background:#3fb8af; color:#0b1210; border:none; }
  button.danger { background:#a8324a; color:#fff; border:none; }
  .channel { background:#1b1f26; border:1px solid #2c313a; border-radius:10px;
             padding:0.9rem 1rem; margin-bottom:0.8rem; }
  .row { display:flex; align-items:center; gap:0.8rem; }
  .row label { width:4.5rem; font-weight:600; }
  .row input[type=range] { flex:1; }
  .row .val { width:3rem; text-align:right; font-variant-numeric:tabular-nums; }
  .btns { display:flex; gap:0.5rem; margin-top:0.5rem; }
  .btns button { flex:1; padding:0.4rem; font-size:0.85rem; }
  .leg { margin-bottom:1.4rem; }
  .leg h2 { font-size:1rem; color:#9c9486; margin:0 0 0.5rem; text-transform:uppercase; letter-spacing:0.05em; }
  .offset { font-size:0.8rem; color:#9c9486; margin-top:0.3rem; font-variant-numeric:tabular-nums; }
</style>
</head>
<body>
  <h1>Momo &middot; Servo Panel</h1>
  <div class="topbar">
    <button class="primary" onclick="allCenter()">All &rarr; 90&deg;</button>
    <button class="danger" onclick="allRelease()">Release All</button>
  </div>
  {% for leg in legs %}
  <div class="leg">
    <h2>{{ leg.name }}</h2>
    {% for joint in [("Hip (swing)", leg.hip), ("Knee (lift)", leg.knee)] %}
    <div class="channel">
      <div class="row">
        <label>{{ joint[0] }}</label>
        <input type="range" min="0" max="180" value="90" id="slider{{ joint[1] }}"
               oninput="onSlide({{ joint[1] }}, this.value)">
        <span class="val" id="val{{ joint[1] }}">90</span>
      </div>
      <div class="offset" id="offset{{ joint[1] }}">offset: {{ "%+d"|format(offsets[joint[1]|string]) }}&deg;</div>
      <div class="btns">
        <button onclick="center({{ joint[1] }})">Center 90&deg;</button>
        <button onclick="release({{ joint[1] }})">Release</button>
        <button class="primary" onclick="setZero({{ joint[1] }})">Set as Zero</button>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endfor %}

<script>
async function post(url, body) {
  await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body || {})
  });
}

function onSlide(ch, angle) {
  document.getElementById("val" + ch).textContent = angle;
  post("/set", {channel: ch, angle: parseInt(angle)});
}

function center(ch) {
  document.getElementById("slider" + ch).value = 90;
  document.getElementById("val" + ch).textContent = 90;
  post("/center", {channel: ch});
}

function release(ch) {
  post("/release", {channel: ch});
}

async function setZero(ch) {
  const res = await fetch("/set_zero", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({channel: ch})
  });
  const data = await res.json();
  document.getElementById("offset" + ch).textContent = "offset: " + (data.offset >= 0 ? "+" : "") + data.offset + "°";
  document.getElementById("slider" + ch).value = 90;
  document.getElementById("val" + ch).textContent = 90;
}

function allCenter() {
  for (let ch = 0; ch < 8; ch++) center(ch);
}

function allRelease() {
  for (let ch = 0; ch < 8; ch++) release(ch);
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


@app.route("/")
def index():
    offsets = {str(ch): servos.get_offset(ch) for ch in range(8)}
    return render_template_string(PAGE, legs=LEGS_ORDER, offsets=offsets)


@app.route("/set", methods=["POST"])
def set_angle():
    data = request.get_json()
    servos.set_channel(int(data["channel"]), int(data["angle"]))
    return "", 204


@app.route("/center", methods=["POST"])
def center():
    data = request.get_json()
    servos.center_channel(int(data["channel"]))
    return "", 204


@app.route("/release", methods=["POST"])
def release():
    data = request.get_json()
    servos.release_channel(int(data["channel"]))
    return "", 204


@app.route("/set_zero", methods=["POST"])
def set_zero():
    data = request.get_json()
    channel = int(data["channel"])
    servos.zero_here(channel)
    return {"offset": servos.get_offset(channel)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
