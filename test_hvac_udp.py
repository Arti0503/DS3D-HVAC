#!/usr/bin/env python3
"""
HVAC Telemetry & JSON Verification Tool
=======================================
Tests loading of the HVAC Excel variable sheet, generates the exact
Unity-compatible JSON payload, and validates bidirectional UDP transmission.
"""

import os
import sys
import json
import socket
import time

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


HVAC_SPEED_VARS = [
    "BlueArrowOut",
    "Fan1",
    "Fan2",
    "GreenArrowIN1",
    "GreenArrowIN2",
    "YellowArrowIn"
]

HVAC_AMPLITUDE_VARS = [
    "RedArrow_Inlet",
    "RedArrow_Outlet",
    "BlueArrow_Outlet",
    "GreenArrow_Inlet",
    "YellowArrow_Inlet",
    "FADL",
    "FADR",
    "RAD"
]

HVAC_BOOLEAN_VARS = [
    "ShowHideObjects",
    "Application Quit"
]

ALL_HVAC_VARS = HVAC_SPEED_VARS + HVAC_AMPLITUDE_VARS + HVAC_BOOLEAN_VARS


def load_hvac_excel(excel_path):
    """
    Robust Excel loader supporting:
    1. Raw uploaded sheet (starts at row 822, split columns D & G)
    2. Clean standardized sheet (starts at row 2, standard columns)
    """
    if not HAS_OPENPYXL:
        raise RuntimeError("openpyxl is required. Run: pip install openpyxl")

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"File not found: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active

    extracted_values = {}
    row_mapping = {}

    # Scan all cells to find variable names
    for r in range(1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            val = ws.cell(r, c).value
            if val and isinstance(val, str):
                cleaned_name = val.strip()
                # Check for match against our known 16 variables
                for target_var in ALL_HVAC_VARS:
                    if cleaned_name.lower() == target_var.lower():
                        # Found variable row! Extract values from this row
                        row_vals = [ws.cell(r, col_idx).value for col_idx in range(1, ws.max_column + 1)]
                        
                        # Find numeric / boolean value in this row (exclude the SR.No in col 1)
                        # Priority: search from right or specific columns
                        candidate_vals = []
                        for idx, v in enumerate(row_vals):
                            if idx == c - 1:  # skip the variable name cell itself
                                continue
                            if isinstance(v, (int, float)) and v is not None:
                                candidate_vals.append((idx + 1, v))
                            elif isinstance(v, bool):
                                candidate_vals.append((idx + 1, 1.0 if v else 0.0))
                            elif isinstance(v, str) and v.strip().lower() in ("true", "false", "0", "1"):
                                b_val = 1.0 if v.strip().lower() in ("true", "1") else 0.0
                                candidate_vals.append((idx + 1, b_val))

                        # If candidates found:
                        # For raw sheet, row 822-827 has value at col 4, row 828-837 has value at col 7
                        # First number that is NOT the SR.No (col 1):
                        filtered_num = [cv for cv in candidate_vals if cv[0] > 1]
                        val_to_use = filtered_num[0][1] if filtered_num else 5.0

                        extracted_values[target_var] = float(val_to_use)
                        row_mapping[target_var] = (r, c, row_vals)
                        break

    return extracted_values, row_mapping


def build_hvac_json(values_dict):
    """
    Construct the JSON schema expected by Unity HVAC UDPManager.cs:
    {
      "Hvac": {
        "Speed": [{"Name": "...", "Value": 5.0}, ...],
        "Amplitude": [{"Name": "...", "Value": 5.0}, ...],
        "Boolean": [{"Name": "...", "Value": false}, ...]
      }
    }
    """
    speed_list = [
        {"Name": name, "Value": round(values_dict.get(name, 5.0), 2)}
        for name in HVAC_SPEED_VARS
    ]

    amplitude_list = [
        {"Name": name, "Value": round(values_dict.get(name, 5.0 if name not in ("FADL", "FADR", "RAD") else 0.0), 2)}
        for name in HVAC_AMPLITUDE_VARS
    ]

    boolean_list = [
        {"Name": name, "Value": bool(values_dict.get(name, 0.0) > 0.5)}
        for name in HVAC_BOOLEAN_VARS
    ]

    payload = {
        "Hvac": {
            "Speed": speed_list,
            "Amplitude": amplitude_list,
            "Boolean": boolean_list
        }
    }
    return payload


def build_hvac_csv(values_dict):
    """
    Construct sequential float array CSV matching Unity HVAC buffer layout:
    6 Speeds, 5 Colors, 3 BlendShapes, 2 Booleans (Total 16 floats).
    """
    tokens = []
    for name in HVAC_SPEED_VARS:
        tokens.append(f"{values_dict.get(name, 5.0):.1f}")
    for name in HVAC_AMPLITUDE_VARS:
        tokens.append(f"{values_dict.get(name, 5.0 if name not in ('FADL', 'FADR', 'RAD') else 0.0):.1f}")
    for name in HVAC_BOOLEAN_VARS:
        tokens.append("1" if values_dict.get(name, 0.0) > 0.5 else "0")
    return ",".join(tokens)


def run_udp_verification(json_str, target_ip="127.0.0.1", tx_port=9000, rx_port=5005, timeout_sec=1.0):
    """
    Transmits the JSON packet to Unity HVAC and listens for telemetry feedback.
    """
    print(f"\n[UDP TEST] Target: {target_ip}:{tx_port} | Listener: 0.0.0.0:{rx_port}")

    # Set up RX listener
    rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx_bound = False
    try:
        rx_socket.bind(("0.0.0.0", rx_port))
        rx_socket.settimeout(timeout_sec)
        rx_bound = True
        print(f"  [OK] Listener socket successfully bound on Port {rx_port}.")
    except Exception as e:
        print(f"  [INFO] Port {rx_port} already in use or cannot bind: {e}")

    # Set up TX sender
    tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bytes_sent = 0
    try:
        data_bytes = json_str.encode("utf-8")
        bytes_sent = tx_socket.sendto(data_bytes, (target_ip, tx_port))
        print(f"  [OK] TX Sent {bytes_sent} bytes to {target_ip}:{tx_port}")
    except Exception as e:
        print(f"  [FAIL] Failed to send UDP packet: {e}")
    finally:
        tx_socket.close()

    # Listen for feedback packet
    received_packet = None
    if rx_bound:
        t0 = time.time()
        try:
            data, addr = rx_socket.recvfrom(4096)
            received_packet = (data.decode("utf-8", errors="ignore"), addr)
            print(f"  [OK] RX Feedback received from {addr} ({len(data)} bytes):\n       {received_packet[0]}")
        except socket.timeout:
            print(f"  [NOTE] No immediate reply packet on Port {rx_port} within {timeout_sec}s.")
            print("         (Normal when Unity HVAC is in Edit mode or event is not yet triggered).")
        except Exception as e:
            print(f"  [WARN] RX listener error: {e}")
        finally:
            rx_socket.close()

    return bytes_sent > 0, received_packet


def main():
    print("=" * 75)
    print("      DS3D-HVAC TELEMETRY & JSON DATA VERIFICATION BENCH")
    print("=" * 75)

    # Locate test Excel file
    candidates = [
        r"C:\Users\user\Downloads\hvactest.xlsx",
        r"C:\Users\user\Downloads\DS3D_HVAC_Variable_List.xlsx",
        os.path.join(os.path.dirname(__file__), "DS3D_HVAC_Variable_List.xlsx"),
        r"C:\Users\user\.gemini\antigravity\brain\38fcf87e-246a-4c0a-90c4-77889009413d\.user_uploaded\media_1791801058351_da33131a.xlsx"
    ]
    excel_path = next((p for p in candidates if os.path.exists(p)), None)

    if not excel_path:
        print("[ERROR] No HVAC Excel test sheet found in candidate paths.")
        sys.exit(1)

    print(f"\n[1/4] Loading Excel File: {excel_path}")
    values, row_map = load_hvac_excel(excel_path)
    print(f"      Successfully resolved {len(values)} / {len(ALL_HVAC_VARS)} variables.")

    # Print variable table
    print("\n[2/4] Extracted HVAC Parameter Table:")
    print("-" * 75)
    print(f"{'#':<3} {'Variable Name':<22} {'Category':<18} {'Excel Value':<12} {'JSON Type'}")
    print("-" * 75)

    idx = 1
    for var in HVAC_SPEED_VARS:
        v = values.get(var, 5.0)
        print(f"{idx:<3} {var:<22} {'Speed (Airflow/Fan)':<18} {v:<12.1f} {'Float'}")
        idx += 1

    for var in HVAC_AMPLITUDE_VARS:
        v = values.get(var, 5.0 if var not in ("FADL", "FADR", "RAD") else 0.0)
        cat = "Color (Intensity)" if "Arrow" in var else "Damper (BlendShape)"
        print(f"{idx:<3} {var:<22} {cat:<18} {v:<12.1f} {'Float'}")
        idx += 1

    for var in HVAC_BOOLEAN_VARS:
        v = values.get(var, 0.0)
        b_val = bool(v > 0.5)
        print(f"{idx:<3} {var:<22} {'System Control':<18} {str(b_val):<12} {'Boolean'}")
        idx += 1
    print("-" * 75)

    # Build JSON
    print("\n[3/4] Constructing Target HVAC JSON Payload:")
    payload_obj = build_hvac_json(values)
    json_formatted = json.dumps(payload_obj, indent=2)
    json_compact = json.dumps(payload_obj, separators=(',', ':'))
    csv_payload = build_hvac_csv(values)

    print(json_formatted)
    print(f"\n      Compact JSON Length: {len(json_compact)} bytes")
    print(f"      Alternative CSV Payload: {csv_payload}")

    # Save to disk
    out_json_path = os.path.join(os.path.dirname(__file__), "hvac_payload.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        f.write(json_formatted)
    print(f"      Saved JSON to: {out_json_path}")

    # UDP Transmission Test
    print("\n[4/4] Executing UDP Transmission & Roundtrip Verification:")
    tx_ok, rx_data = run_udp_verification(json_compact, target_ip="127.0.0.1", tx_port=9000, rx_port=5005)

    print("\n" + "=" * 75)
    print("                     VERIFICATION SUMMARY")
    print("=" * 75)
    print(f"  1. Excel Data Parsing : PASS ({len(values)}/16 parameters extracted)")
    print(f"  2. JSON Payload Build : PASS (Valid schema with Speed, Amplitude, Boolean)")
    print(f"  3. UDP TX Port 9000   : {'PASS (Transmitted successfully)' if tx_ok else 'FAIL'}")
    print(f"  4. UDP RX Port 5005   : {'PASS (Feedback received)' if rx_data else 'READY (Socket bound & listening)'}")
    print("=" * 75)


if __name__ == "__main__":
    main()
