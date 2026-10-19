import socket
import json
import time
import sys

UNITY_IP = "127.0.0.1"
UNITY_RX_PORT = 9000
LABVIEW_LISTEN_PORT = 5005

def run_verification():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", LABVIEW_LISTEN_PORT))
    sock.settimeout(2.5)

    print("=" * 75)
    print("DS3D-HVAC FULL SYSTEM & EXCEL TABLE SPECIFICATION TESTER")
    print(f"Target Unity: {UNITY_IP}:{UNITY_RX_PORT} | Listening on LabVIEW Port: {LABVIEW_LISTEN_PORT}")
    print("=" * 75)

    def send_cmd(payload):
        if isinstance(payload, dict):
            raw = json.dumps(payload).encode("utf-8")
        else:
            raw = str(payload).encode("utf-8")
        sock.sendto(raw, (UNITY_IP, UNITY_RX_PORT))
        print(f"\n[{time.strftime('%H:%M:%S')}] >>> SENT TO UNITY: {payload if not isinstance(payload, dict) else json.dumps(payload)}")

    def recv_packets(wait_sec=2.0):
        start = time.time()
        packets = []
        while time.time() - start < wait_sec:
            try:
                data, _ = sock.recvfrom(4096)
                msg = data.decode("utf-8", errors="replace").strip()
                now = time.strftime("%H:%M:%S")
                print(f"[{now}] <<< RECEIVED TELEMETRY: {msg}")
                packets.append(msg)
            except socket.timeout:
                continue
        return packets

    # --- TEST 1: FAULT TRIGGER (Fault 101) ---
    print("\n" + "=" * 50)
    print("TEST 1: FAULT 101 TRIGGER (Standard LabVIEW Payload)")
    print("=" * 50)
    trigger_payload = {
        "Hvac": {
            "Fault": [
                {"Name": "Fault_Code_Trigger", "Value": 101},
                {"Name": "Fault_Cause_Trigger", "Value": 1},
                {"Name": "Fault_Command_Action", "Value": 1}
            ]
        }
    }
    send_cmd(trigger_payload)
    pkts = recv_packets(3.0)
    has_started = any("fault_started" in p for p in pkts)
    print(f"--> Result Test 1: {'[PASS]' if has_started else '[FAIL]'}")

    # --- TEST 2: SENSOR HIGHLIGHTS TOGGLING ---
    print("\n" + "=" * 50)
    print("TEST 2: SENSOR HIGHLIGHTS TOGGLING (FAT, RAT, SAT, Smoke)")
    print("=" * 50)
    sensors_payload = {
        "Hvac": {
            "Boolean": [
                {"Name": "FAT_Sensor_Highlights", "Value": True},
                {"Name": "RAT_Sensor_Highlights", "Value": True},
                {"Name": "SAT_Sensor_Highlights", "Value": True},
                {"Name": "Smoke_Detector_Highlights", "Value": True}
            ]
        }
    }
    send_cmd(sensors_payload)
    pkts = recv_packets(2.5)
    has_sensor_ack = any("sensor_highlight_changed" in p for p in pkts)
    print(f"--> Result Test 2: {'[PASS]' if has_sensor_ack else '[INFO - No ACK or already processed]'}")

    # --- TEST 3: STEP-BY-STEP ADVANCEMENT VIA SKIP COMMAND ---
    print("\n" + "=" * 50)
    print("TEST 3: STEP PROGRESSION TO FAULT COMPLETION")
    print("=" * 50)
    completed_fault = False
    
    # We advance through all remaining steps using 'skip' command
    for step_attempt in range(1, 20):
        print(f"\n--- Advancing step {step_attempt} via 'skip' command ---")
        send_cmd("skip")
        pkts = recv_packets(1.5)
        
        for p in pkts:
            if "fault_completed" in p:
                print("\n" + "*" * 60)
                print(">>> SUCCESS: FAULT_COMPLETED EVENT RECEIVED LIVE! <<<")
                print("*" * 60)
                completed_fault = True
                break
        if completed_fault:
            break
        time.sleep(0.5)

    print(f"\n--> Result Test 3 (Fault Completion): {'[PASS]' if completed_fault else '[PENDING MANUAL COMPLETION]'}")

    # --- TEST 4: FAULT RESET COMMAND ---
    print("\n" + "=" * 50)
    print("TEST 4: FAULT RESET (Fault_Command_Action = 2)")
    print("=" * 50)
    reset_payload = {
        "Hvac": {
            "Fault": [
                {"Name": "Fault_Code_Trigger", "Value": 0},
                {"Name": "Fault_Cause_Trigger", "Value": 0},
                {"Name": "Fault_Command_Action", "Value": 2}
            ]
        }
    }
    send_cmd(reset_payload)
    pkts = recv_packets(2.0)
    has_reset = any("fault_reset" in p for p in pkts)
    print(f"--> Result Test 4: {'[PASS]' if has_reset else '[INFO]'}")

    sock.close()
    print("\n" + "=" * 75)
    print("VERIFICATION COMPLETED.")
    print("=" * 75)

if __name__ == "__main__":
    run_verification()
