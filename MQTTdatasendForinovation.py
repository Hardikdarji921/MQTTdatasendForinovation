import json
import random
import time
from datetime import datetime
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
START = dtime(9, 0)    # 09:00 IST
END = dtime(18, 0)     # 18:00 IST

def generate_payload():
    now = datetime.now(ZoneInfo("Asia/Kolkata"))

    payload = {
        # ---- Device ----
        "Device_ID": "AP550",

        # ---- SD Card ----
        "sd_free_mb": round(random.uniform(100, 1024), 1),
        "sd_free_pc": random.randint(50, 55),

        # ---- Engine / Machine ----
        "Engine_status": "ON",
        "Engine_rpm": random.randint(2100, 2200),
        "fuel_level": round(random.uniform(55, 60), 1),
        "def_level": round(random.uniform(65, 70), 1),
        "Coolant_temp": round(random.uniform(60, 70), 1),
        "oil_Pressure": round(random.uniform(200, 250), 1),
        "wif": random.choice([0, 1]),

        # ---- Hour Counters ----
        "engine_h": round(random.uniform(300, 310), 1),
        "idle_h": round(random.uniform(100, 110), 1),
        "work_h": round(random.uniform(150, 155), 1),
        "travel_h": round(random.uniform(100, 105), 1),
        "vibration_h": round(random.uniform(50, 55), 1),
        "heating_h": round(random.uniform(30, 33), 1),
        "tamper_h": round(random.uniform(50, 55), 1),

        # ---- Electrical ----
        "battery": round(random.uniform(11.5, 14.8), 2),

        # ---- GPS ----
        "lat": "23.0225",
        "lon": "72.5714",
        "machine_type": "CEV_V",
        "machine_model": "AP550",
        "ESP_firmware": "0.0.0.1",
        "machine_version": "0.0.1.0",
        "Vin_number": "abc123456dv789532",
        
        # ---- DTCs ----
        "engine_dtc": "0/0/0",
        "ttc_dtc": "0/0/0",

        # ---- Timestamp ----
        "time": now.strftime("%d-%m-%Y %I:%M:%S %p")
    }

    return json.dumps(payload)

# ================= MQTT =================
client = mqtt.Client(
    client_id=CLIENT_ID,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.connect(BROKER, PORT, 60)
client.loop_start()

print("🔥 Dummy MQTT sender running (FULL ESP32 PAYLOAD)")


while True:
    now_dt = datetime.now(IST)
    now_time = now_dt.time()
    weekday = now_dt.weekday()  # 0=Mon, 6=Sun

    if 0 <= weekday <= 4 and START <= now_time <= END:
        payload = generate_payload()
        client.publish(TOPIC, payload)
        print("➡ Sent:", payload)
        time.sleep(PUBLISH_INTERVAL)
    else:
        print("⏹ Outside working hours. Exiting.")
        break



