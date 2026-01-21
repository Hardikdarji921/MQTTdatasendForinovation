import json
import random
import time
from datetime import datetime, time as dtime
import paho.mqtt.client as mqtt
from zoneinfo import ZoneInfo

# ================= CONFIG =================
BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "Datalogger/AP550/Data"
CLIENT_ID = "python_dummy_datalogger"
PUBLISH_INTERVAL = 20
# ==========================================

IST = ZoneInfo("Asia/Kolkata")
START = dtime(9, 0)
END = dtime(18, 0)

# -------- Engine State --------
engine = {
    "on": True,
    "rpm": 800.0,
    "fuel": 60.0,
    "adblue": 70.0,
    "coolant": 30.0,
    "oil_temp": 35.0,
    "oil_pressure": 220.0,
    "exhaust_temp": 120.0,
    "boost": 0.2,
    "load": 0.2,
    "torque": 200.0,
    "battery": 12.6,
    "alternator": 13.8,
    "vibration": 0.1,
    "engine_h": 300.0,
}

# -------- Load / Save Hours --------
HOUR_FILE = "hours.json"

def load_hours():
    try:
        with open(HOUR_FILE, "r") as f:
            data = json.load(f)
            engine["engine_h"] = data.get("engine_h", engine["engine_h"])
            print("✅ Loaded engine_h:", engine["engine_h"])
    except:
        print("⚠ No previous hour file, using default.")

def save_hours():
    with open(HOUR_FILE, "w") as f:
        json.dump({"engine_h": engine["engine_h"]}, f)

load_hours()

# -------- Fault Model --------
FAULTS = [
    {"spn": 100, "fmi": 1, "desc": "Engine Oil Pressure Low"},
    {"spn": 110, "fmi": 0, "desc": "Coolant Temperature High"},
    {"spn": 157, "fmi": 18, "desc": "Fuel Pressure Low"},
    {"spn": 190, "fmi": 3, "desc": "Engine Overspeed"},
    {"spn": 97,  "fmi": 4, "desc": "Water In Fuel"},
]

active_fault = None
fault_timer = 0

def update_engine():
    global active_fault, fault_timer

    if engine["on"]:
        target_rpm = random.randint(1600, 2200)
        engine["rpm"] += (target_rpm - engine["rpm"]) * 0.08

        engine["load"] = min(1.0, max(0.2, engine["rpm"] / 2200))
        engine["boost"] = engine["load"] * random.uniform(0.8, 1.2)
        engine["torque"] = engine["load"] * random.uniform(350, 500)

        engine["fuel"] -= engine["load"] * random.uniform(0.01, 0.03)
        engine["fuel"] = max(engine["fuel"], 0)

        engine["adblue"] -= engine["load"] * random.uniform(0.002, 0.006)
        engine["adblue"] = max(engine["adblue"], 0)
        if engine["adblue"] < 10 and random.random() < 0.05:
            engine["adblue"] = random.uniform(60, 80)

        engine["coolant"] += engine["load"] * random.uniform(0.2, 0.5)
        engine["coolant"] = min(engine["coolant"], 95)

        engine["oil_temp"] += engine["load"] * random.uniform(0.2, 0.4)
        engine["oil_temp"] = min(engine["oil_temp"], 110)

        engine["oil_pressure"] = 150 + engine["rpm"] * 0.05
        engine["exhaust_temp"] = 150 + engine["load"] * 500

        engine["battery"] = min(14.4, engine["battery"] + 0.01)
        engine["alternator"] = 13.5 + engine["load"] * 0.8
        engine["vibration"] = 0.1 + engine["load"] * 0.5

        engine["engine_h"] += PUBLISH_INTERVAL / 3600
    else:
        engine["rpm"] = max(0, engine["rpm"] - 400)
        engine["coolant"] = max(25, engine["coolant"] - 0.3)
        engine["oil_temp"] = max(25, engine["oil_temp"] - 0.3)
        engine["exhaust_temp"] = max(100, engine["exhaust_temp"] - 5)
        engine["boost"] = 0
        engine["load"] = 0
        engine["torque"] = 0
        engine["oil_pressure"] = max(0, engine["oil_pressure"] - 20)

    if random.random() < 0.005:
        engine["on"] = not engine["on"]

    if active_fault:
        fault_timer -= 1
        if fault_timer <= 0:
            active_fault = None
    else:
        if random.random() < 0.02:
            active_fault = random.choice(FAULTS)
            fault_timer = random.randint(5, 20)

    if active_fault:
        if active_fault["spn"] == 100:
            engine["oil_pressure"] *= 0.7
        elif active_fault["spn"] == 110:
            engine["coolant"] += 1.5
        elif active_fault["spn"] == 190:
            engine["rpm"] = min(engine["rpm"] + 300, 2600)

def generate_payload():
    update_engine()
    now = datetime.now(IST)

    payload = {
        "Device_ID": "AP550",
        "Engine_status": "ON" if engine["on"] else "OFF",
        "Engine_rpm": int(engine["rpm"]),
        "Engine_load": round(engine["load"] * 100, 1),
        "Engine_torque": round(engine["torque"], 1),
        "Boost_bar": round(engine["boost"], 2),
        "fuel_level": round(engine["fuel"], 1),
        "def_level": round(engine["adblue"], 1),
        "Coolant_temp": round(engine["coolant"], 1),
        "Oil_temp": round(engine["oil_temp"], 1),
        "oil_Pressure": round(engine["oil_pressure"], 1),
        "Exhaust_temp": round(engine["exhaust_temp"], 1),
        "battery": round(engine["battery"], 2),
        "alternator_v": round(engine["alternator"], 2),
        "vibration": round(engine["vibration"], 2),
        "engine_h": round(engine["engine_h"], 2),
        "lat": "23.0225",
        "lon": "72.5714",
    }

    if active_fault:
        payload["engine_dtc"] = f'{active_fault["spn"]}/{active_fault["fmi"]}'
        payload["dtc_desc"] = active_fault["desc"]
    else:
        payload["engine_dtc"] = "0/0"
        payload["dtc_desc"] = "NO FAULT"

    payload["time"] = now.strftime("%d-%m-%Y %I:%M:%S %p")
    payload["timezone"] = "Asia/Kolkata"

    return json.dumps(payload)

# ================= MQTT =================
client = mqtt.Client(client_id=CLIENT_ID,
                     callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER, PORT, 60)
client.loop_start()

print("🔥 Engine simulator running (9–6 IST, Mon–Fri)")

while True:
    now_dt = datetime.now(IST)
    now_time = now_dt.time()
    weekday = now_dt.weekday()

    if 0 <= weekday <= 4 and START <= now_time <= END:
        payload = generate_payload()
        client.publish(TOPIC, payload)
        print("➡ Sent:", payload)
        save_hours()
        time.sleep(PUBLISH_INTERVAL)
    else:
        print("⏹ Outside working hours. Saving hours and exiting.")
        save_hours()
        break
