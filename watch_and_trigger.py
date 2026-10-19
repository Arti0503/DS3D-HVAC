import socket
import json
import time
import sys

UNITY_IP = "127.0.0.1"
UNITY_RX_PORT = 9000
LABVIEW_LISTEN_PORT = 5005

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", LABVIEW_LISTEN_PORT))
    sock.settimeout(2.0)

    print("=" * 65)
    print("DS3D-HVAC V5 - LIVE UDP TELEMETRY MONITOR")
    print(f"Listening on UDP port {LABVIEW_LISTEN_PORT} | Target Unity: {UNITY_IP}:{UNITY_RX_PORT}")
    print("=" * 65)

    # 1. Trigger Fault 101
    payload = {
        "Hvac": {
            "Fault": [
                {"Name": "Fault_Code_Trigger", "Value": 101},
                {"Name": "Fault_Cause_Trigger", "Value": 1},
                {"Name": "Fault_Command_Action", "Value": 1}
            ]
        }
    }
    raw = json.dumps(payload).encode("utf-8")
    sock.sendto(raw, (UNITY_IP, UNITY_RX_PORT))
    print(f"[{time.strftime('%H:%M:%S')}] >>> SENT FAULT 101 TRIGGER TO UNITY")

    # 2. Continuous listen loop
    print(f"[{time.strftime('%H:%M:%S')}] Monitoring for incoming packets (fault_started, step_completed, fault_completed)...")
    print("Perform steps or click 'Submit Repaired Fault' in Unity to observe events in real-time.\n")

    start_time = time.time()
    # Run for 60 seconds
    try:
        while time.time() - start_time < 60:
            try:
                data, addr = sock.recvfrom(4096)
                msg = data.decode("utf-8", errors="replace").strip()
                now = time.strftime("%H:%M:%S")
                print(f"[{now}] <<< TELEMETRY FROM UNITY: {msg}\n")
                sys.stdout.flush()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")
    finally:
        sock.close()
        print("Live monitor finished.")

if __name__ == "__main__":
    main()
