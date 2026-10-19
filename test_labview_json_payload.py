#!/usr/bin/env python3
"""
Test LabVIEW Proposed JSON Schema for DS3D-HVAC
================================================
Validates that Unity seamlessly supports:
1. "Fault" array with Fault_Code_Trigger, Fault_Cause_Trigger, and Fault_Command_Action (1: Trigger, 2: Reset, 0: Idle).
2. "Boolean" array with mixed numeric (0/1) and boolean values, plus individual compressor highlights (Compresor 1..4_Highlights).
3. "Spare" array with reserved telemetry channels.
4. "Speed" and "Amplitude" animation/slider telemetry.
"""

import socket
import json
import time

UNITY_IP = "127.0.0.1"
UNITY_RX_PORT = 9000
LABVIEW_LISTEN_PORT = 5005

def build_payload(fault_code=0, fault_cause=0, fault_command=0, comp1=True, comp2=True, comp3=True, comp4=True):
    return {
        "Hvac": {
            "Speed": [
                {"Name": "BlueArrowOut", "Value": 5},
                {"Name": "Fan1", "Value": 0},
                {"Name": "Fan2", "Value": 0},
                {"Name": "GreenArrowIN1", "Value": 5},
                {"Name": "GreenArrowIN2", "Value": 5},
                {"Name": "YellowArrowIn", "Value": 5}
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
                {"Name": "DS3D_OFF", "Value": 0},
                {"Name": "ShowHideObjects", "Value": False},
                {"Name": "Compresor 1_Highlights", "Value": comp1},
                {"Name": "Compresor 2_Highlights", "Value": comp2},
                {"Name": "Compresor 3_Highlights", "Value": comp3},
                {"Name": "Compresor 4_Highlights", "Value": comp4}
            ],
            "Fault": [
                {"Name": "Fault_Code_Trigger", "Value": fault_code},
                {"Name": "Fault_Cause_Trigger", "Value": fault_cause},
                {"Name": "Fault_Command_Action", "Value": fault_command}
            ],
            "Spare": [
                {"Name": "Spare_24", "Value": 0},
                {"Name": "Spare_25", "Value": 0},
                {"Name": "Spare_26", "Value": 0},
                {"Name": "Spare_27", "Value": 0},
                {"Name": "Spare_28", "Value": 0},
                {"Name": "Spare_29", "Value": 0},
                {"Name": "Spare_30", "Value": 0}
            ]
        }
    }

def send_and_listen(payload, description=""):
    print("\n" + "=" * 70)
    print(f"STEP: {description}")
    print("=" * 70)

    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("0.0.0.0", LABVIEW_LISTEN_PORT))
        listener.settimeout(1.5)
    except Exception as e:
        print(f"[NOTE] Listener bind notice: {e}")

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    raw_data = json.dumps(payload, indent=2).encode("utf-8")
    sender.sendto(raw_data, (UNITY_IP, UNITY_RX_PORT))
    sender.close()
    print(f"[SENT] {len(raw_data)} bytes -> {UNITY_IP}:{UNITY_RX_PORT}")

    try:
        while True:
            data, addr = listener.recvfrom(4096)
            msg = data.decode("utf-8")
            print(f"[RECV TELEMETRY] From {addr}: {msg}")
    except socket.timeout:
        print("[DONE] Listen window closed (timeout reached).")
    except Exception as ex:
        print(f"[NOTE] {ex}")
    finally:
        listener.close()

if __name__ == "__main__":
    print("Testing LabVIEW Proposed JSON Format against Unity DS3D-HVAC...")

    # Test 1: Idle stream (normal operations, all highlights ON)
    payload_idle = build_payload(fault_code=0, fault_command=0, comp1=True, comp2=True, comp3=True, comp4=True)
    send_and_listen(payload_idle, "1. Idle Telemetry Stream (Fault_Command_Action = 0)")

    time.sleep(0.5)

    # Test 2: Trigger Fault 101 via Fault_Command_Action = 1
    payload_trigger = build_payload(fault_code=101, fault_cause=1, fault_command=1, comp1=False, comp2=False, comp3=False, comp4=False)
    send_and_listen(payload_trigger, "2. Trigger Fault 101 (Fault_Command_Action = 1, Fault_Code_Trigger = 101)")

    time.sleep(1.0)

    # Test 3: Reset Fault via Fault_Command_Action = 2
    payload_reset = build_payload(fault_code=0, fault_command=2, comp1=True, comp2=True, comp3=True, comp4=True)
    send_and_listen(payload_reset, "3. Reset Fault (Fault_Command_Action = 2)")

    time.sleep(0.5)

    # Test 4: Individual Compressor Highlights
    payload_comp = build_payload(fault_code=0, fault_command=0, comp1=True, comp2=False, comp3=True, comp4=False)
    send_and_listen(payload_comp, "4. Individual Compressor Highlights (Comp 1 & 3 ON, Comp 2 & 4 OFF)")
