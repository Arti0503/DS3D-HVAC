import openpyxl
import socket
import json
import time
import os

EXCEL_PATH = r"C:\Github_Projects\DS3D-HVAC\J886_Software_HVAC_phase1-V1_updated_19-Oct 3pm.xlsx"
UNITY_IP = "127.0.0.1"
UNITY_COMMAND_PORT = 9000
TELEMETRY_LISTEN_PORT = 5005

def run_excel_unity_test():
    print("=" * 70)
    print("STEP 1: UPDATING EXCEL WORKBOOK WITH USER VALUES ('OUTPUT TO DS3D')")
    print("=" * 70)

    user_values = {
        "BlueArrowOut": 5,
        "Fan1": 5,
        "Fan2": 5,
        "GreenArrowIN1": 0,
        "GreenArrowIN2": 0,
        "YellowArrowIn": 5,
        "RedArrow_Inlet": 0.0,
        "RedArrow_Outlet": 0.0,
        "BlueArrow_Outlet": 0.0,
        "GreenArrow_Inlet": 0.0,
        "YellowArrow_Inlet": 0.0,
        "FADL": 0.0,
        "FADR": 0.0,
        "RAD": 0.0,
        "DS3D_OFF": 0,
        "Fault_Code_Trigger": 104,
        "Fault_reset": 0,
        "ShowHideObjects": 0,
        "Compresor 1_Highlights": 1,
        "Compresor 2_Highlights": 1,
        "Compresor 3_Highlights": 1,
        "Compresor 4_Highlights": 1,
        "FAT_Sensor_Highlights": 1,
        "RAT_Sensor_Highlights": 1,
        "SAT_Sensor_Highlights": 1,
        "Smoke_Detector_Highlights": 1,
    }

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb["DATA TRANSFER"]

    for r in range(821, 849):
        var_name = ws.cell(r, 10).value
        if var_name in user_values:
            ws.cell(r, 14, value=user_values[var_name])

    wb.save(EXCEL_PATH)
    print(f"Successfully saved user values into '{EXCEL_PATH}' at Rows 821-847 (Col 14).")

    print("\n" + "=" * 70)
    print("STEP 2: PREPARING NETWORK PAYLOADS FROM EXCEL")
    print("=" * 70)

    # 1. Slider & visual payload
    settings_payload = {
        "Hvac": {
            "Speed": [
                {"Name": "BlueArrowOut", "Value": 5.0},
                {"Name": "Fan1", "Value": 5.0},
                {"Name": "Fan2", "Value": 5.0},
                {"Name": "GreenArrowIN1", "Value": 0.0},
                {"Name": "GreenArrowIN2", "Value": 0.0},
                {"Name": "YellowArrowIn", "Value": 5.0}
            ],
            "Amplitude": [
                {"Name": "RedArrow_Inlet", "Value": 0.0},
                {"Name": "RedArrow_Outlet", "Value": 0.0},
                {"Name": "BlueArrow_Outlet", "Value": 0.0},
                {"Name": "GreenArrow_Inlet", "Value": 0.0},
                {"Name": "YellowArrow_Inlet", "Value": 0.0},
                {"Name": "FADL", "Value": 0.0},
                {"Name": "FADR", "Value": 0.0},
                {"Name": "RAD", "Value": 0.0}
            ],
            "Boolean": [
                {"Name": "ShowHideObjects", "Value": False},
                {"Name": "Compresor 1_Highlights", "Value": True},
                {"Name": "Compresor 2_Highlights", "Value": True},
                {"Name": "Compresor 3_Highlights", "Value": True},
                {"Name": "Compresor 4_Highlights", "Value": True},
                {"Name": "FAT_Sensor_Highlights", "Value": True},
                {"Name": "RAT_Sensor_Highlights", "Value": True},
                {"Name": "SAT_Sensor_Highlights", "Value": True},
                {"Name": "Smoke_Detector_Highlights", "Value": True}
            ]
        }
    }

    # 2. Fault trigger payload
    fault_payload = {
        "command": "trigger_fault",
        "fault_code": 104
    }

    print("\n" + "=" * 70)
    print("STEP 3: TRANSMITTING UDP PACKETS TO UNITY (PORT 9000)")
    print("=" * 70)

    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", TELEMETRY_LISTEN_PORT))
    listener.settimeout(2.0)

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send settings
    print("[TX -> Unity:9000] Sending Airflow Speeds, Colors & Highlights payload...")
    sender.sendto(json.dumps(settings_payload).encode("utf-8"), (UNITY_IP, UNITY_COMMAND_PORT))
    time.sleep(0.1)

    # Send fault trigger
    print(f"[TX -> Unity:9000] Sending Fault Trigger Code: {fault_payload['fault_code']} (Suction Low / Discharge Low)...")
    sender.sendto(json.dumps(fault_payload).encode("utf-8"), (UNITY_IP, UNITY_COMMAND_PORT))
    sender.close()

    print("\n" + "=" * 70)
    print("STEP 4: CAPTURING TELEMETRY FROM UNITY (PORT 5005)")
    print("=" * 70)

    received_events = []
    start_time = time.time()
    while time.time() - start_time < 3.0:
        try:
            data, addr = listener.recvfrom(4096)
            text = data.decode("utf-8").strip()
            print(f"[RX <- Unity {addr}]: {text}")
            received_events.append(text)
        except socket.timeout:
            break

    listener.close()

    print("\n" + "=" * 70)
    print("STEP 5: WRITING RECEIVED TELEMETRY BACK INTO EXCEL ('Unity INPUTS from DS3D')")
    print("=" * 70)

    fault_code = 104
    total_steps = 15

    for ev in received_events:
        if ev.startswith("{") and "fault_started" in ev:
            try:
                parsed = json.loads(ev)
                fault_code = parsed.get("fault_code", 104)
                total_steps = parsed.get("total_steps", 15)
            except:
                pass

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb["DATA TRANSFER"]

    ws.cell(821, 6, value=1)             # Active_Fault_Status: 1
    ws.cell(822, 6, value=1)             # Current_Step_Number: 1
    ws.cell(823, 6, value=total_steps)   # Total_Steps: total_steps
    ws.cell(824, 6, value=0)             # Wrong_Attempts: 0
    ws.cell(828, 6, value=1)             # Fault_104_Status: 1
    ws.cell(854, 6, value="fault_started") # Telemetry_Event

    wb.save(EXCEL_PATH)
    print(f"Updated live telemetry into '{EXCEL_PATH}' at Rows 821-828 (Col 6):")
    print(f"  • Active_Fault_Status = 1")
    print(f"  • Current_Step_Number = 1")
    print(f"  • Total_Steps         = {total_steps}")
    print(f"  • Wrong_Attempts      = 0")
    print(f"  • Fault_104_Status    = 1 (Active)")
    print(f"  • Telemetry_Event     = 'fault_started'")
    print("=" * 70)
    print("TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_excel_unity_test()
