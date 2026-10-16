#!/usr/bin/env python3
"""
Test HVAC Fault & Step Progress UDP Protocol
============================================
Simulates LabVIEW sending fault commands to Unity (Port 9000)
and receiving step progress & fault completion telemetry (Port 5005).
"""

import socket
import json
import time

UNITY_IP = "127.0.0.1"
UNITY_RX_PORT = 9000  # Port where Unity listens
LABVIEW_LISTEN_PORT = 5005  # Port where LabVIEW listens

def test_trigger_fault(fault_code=101, raw_mode=False):
    print("=" * 60)
    print(f"TEST: Triggering Fault {fault_code} (Raw: {raw_mode})")
    print("=" * 60)

    # Prepare listener for response from Unity
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", LABVIEW_LISTEN_PORT))
    listener.settimeout(2.0)

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if raw_mode:
        payload = str(fault_code).encode("utf-8")
        print(f"Sending Raw String: '{fault_code}' -> {UNITY_IP}:{UNITY_RX_PORT}")
    else:
        cmd = {"command": "trigger_fault", "fault_code": fault_code}
        payload = json.dumps(cmd).encode("utf-8")
        print(f"Sending JSON: {json.dumps(cmd)} -> {UNITY_IP}:{UNITY_RX_PORT}")

    sender.sendto(payload, (UNITY_IP, UNITY_RX_PORT))
    sender.close()

    # Try to receive acknowledgment from Unity (if in play mode)
    try:
        data, addr = listener.recvfrom(4096)
        msg = data.decode("utf-8")
        print(f"[RECV] From Unity {addr}: {msg}")
    except socket.timeout:
        print("[NOTE] No packet received within 2s (normal if Unity Editor is not currently in Play mode).")
    finally:
        listener.close()

if __name__ == "__main__":
    print("DS3D-HVAC UDP Fault Communication Test")
    print("---------------------------------------")
    test_trigger_fault(101, raw_mode=False)
    time.sleep(0.5)
    test_trigger_fault(102, raw_mode=True)
