import socket
import json
import time
import subprocess
import threading
import sys
import os

BUILD_EXE = r"C:\Github_Projects\Hvac_Builds\HVAC_V5\DS3D_HVAC.exe"
UNITY_IP = "127.0.0.1"
UNITY_RX_PORT = 9000
LABVIEW_LISTEN_PORT = 5005

stop_event = threading.Event()
received_messages = []

def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", LABVIEW_LISTEN_PORT))
    sock.settimeout(1.0)
    print(f"[TEST HARNESS] Listening on UDP port {LABVIEW_LISTEN_PORT} (Simulating LabVIEW RX)...")

    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(4096)
            text = data.decode("utf-8", errors="replace").strip()
            timestamp = time.strftime("%H:%M:%S")
            received_messages.append((timestamp, text))
            print(f"\n[{timestamp}] <<< RECEIVED FROM UNITY: {text}")
        except socket.timeout:
            continue
        except Exception as e:
            if not stop_event.is_set():
                print(f"[TEST HARNESS] Listener Error: {e}")
            break
    sock.close()

def send_to_unity(payload_dict):
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    raw = json.dumps(payload_dict).encode("utf-8")
    sender.sendto(raw, (UNITY_IP, UNITY_RX_PORT))
    sender.close()
    print(f"\n>>> SENT TO UNITY ({UNITY_RX_PORT}): {json.dumps(payload_dict, indent=2)}")

def check_process_running(process_name):
    try:
        output = subprocess.check_output(f'tasklist /FI "IMAGENAME eq {process_name}"', shell=True).decode()
        return process_name.lower() in output.lower()
    except Exception:
        return False

def main():
    print("=" * 70)
    print("DS3D-HVAC V5 BUILD VERIFICATION HARNESS")
    print("Target: " + BUILD_EXE)
    print("=" * 70)

    # 1. Start listener thread
    listener_thread = threading.Thread(target=udp_listener, daemon=True)
    listener_thread.start()
    time.sleep(1)

    # 2. Check if build is running; if not, launch it
    is_running = check_process_running("DS3D_HVAC.exe")
    if not is_running:
        print("[TEST HARNESS] Launching DS3D_HVAC.exe...")
        subprocess.Popen([BUILD_EXE], cwd=os.path.dirname(BUILD_EXE))
        print("[TEST HARNESS] Waiting 6 seconds for Unity initialization and UDP startup...")
        time.sleep(6)
    else:
        print("[TEST HARNESS] DS3D_HVAC.exe is already running.")

    # 3. Test Fault Trigger 101 via standard LabVIEW JSON format
    print("\n--- STEP 1: Sending Fault 101 Trigger ---")
    fault_trigger_payload = {
        "Hvac": {
            "Fault": [
                {"Name": "Fault_Code_Trigger", "Value": 101},
                {"Name": "Fault_Cause_Trigger", "Value": 1},
                {"Name": "Fault_Command_Action", "Value": 1}
            ]
        }
    }
    send_to_unity(fault_trigger_payload)

    # Wait 3 seconds to capture ack
    time.sleep(3)

    # 4. Monitor loop - keep alive for 15 seconds so we see telemetry
    print("\n[TEST HARNESS] Listening for incoming telemetry (steps, highlights, completion)...")
    print("[TEST HARNESS] (You can interact with the Unity window now. Watching for 15 seconds...)")
    
    start_time = time.time()
    while time.time() - start_time < 15:
        time.sleep(1)

    print("\n" + "=" * 70)
    print("SUMMARY OF RECEIVED TELEMETRY:")
    print("=" * 70)
    if not received_messages:
        print("[WARNING] No messages received from Unity. Check firewall or port binding.")
    else:
        for ts, msg in received_messages:
            print(f"[{ts}] {msg}")

    stop_event.set()
    time.sleep(1)
    print("[TEST HARNESS] Completed.")

if __name__ == "__main__":
    main()
