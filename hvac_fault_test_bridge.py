"""
HVAC Fault Management & Telemetry Test Bridge
Simulates the LabVIEW <-> Unity DS3D interaction:
1. Dispatches fault triggers and commands to Unity (Port 9000).
2. Listens for live step progress and scoring telemetry from Unity (Port 5005).
3. Reads from and writes back to the Master Excel workbook (DATA TRANSFER sheet).
"""

import sys
import os
import time
import json
import socket
import threading
from typing import Optional, Dict, Any

try:
    import openpyxl
except ImportError:
    openpyxl = None

# Network Configuration
UNITY_IP = "127.0.0.1"
UNITY_COMMAND_PORT = 9000   # Unity listens here
TELEMETRY_LISTEN_PORT = 5005  # Unity sends telemetry here

# Candidate Excel file paths (checked in order)
EXCEL_CANDIDATES = [
    r"C:\Users\user\Downloads\J886_Software_HVAC_phase1-V1_Fault_Management_Updated.xlsx",
    r"C:\Users\user\Downloads\J886_Software_HVAC_phase1-V1_updated_13 O0CT 1757 PM.xlsx",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "J886_Software_HVAC_phase1-V1_Fault_Management_Updated.xlsx"),
]

# Fault Catalog Reference (Code -> (Title, Steps))
FAULT_CATALOG = {
    101: ("No HVAC operations", 14),
    102: ("No ventilation", 22),
    103: ("Reduced ventilation", 15),
    104: ("Suction low and discharge low (Circuit 1)", 15),
    105: ("Suction low and discharge low (Circuit 2)", 14),
    106: ("High suction and high discharge", 26),
    107: ("Compressor not operating", 40),
    108: ("Reduced cooling", 33),
    109: ("No Heating", 15),
    110: ("Over Cooling", 8),
    111: ("Over Heating", 7),
    112: ("No emergency ventilation", 14),
    113: ("Smoke identified in saloon", 13),
    114: ("Compressor excessively noisy | Condenser Fan / Blower", 36),
    115: ("Spare Fault Scenario 15", 10),
    116: ("Spare Fault Scenario 16", 10),
}

# Terminal colors for clean visibility
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Global state
excel_lock = threading.Lock()
active_excel_path: Optional[str] = None
receiver_running = True


def find_excel_file() -> Optional[str]:
    """Finds the first existing candidate Excel file."""
    for path in EXCEL_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def read_trigger_from_excel(filepath: str) -> Dict[str, Any]:
    """Reads instructor trigger parameters from DATA TRANSFER."""
    if not openpyxl:
        return {"fault_code": 0, "cause_code": 0, "action": 0}

    with excel_lock:
        try:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            ws = wb["DATA TRANSFER"]
            # F1209: Fault Number, F1210: Cause Number, F1211: Command Action
            fault_code = ws.cell(row=1209, column=6).value or ws.cell(row=837, column=14).value or 0
            cause_code = ws.cell(row=1210, column=6).value or ws.cell(row=838, column=14).value or 0
            action = ws.cell(row=1211, column=6).value or ws.cell(row=839, column=14).value or 0

            # Convert to int if string
            try:
                fault_code = int(fault_code)
            except (ValueError, TypeError):
                fault_code = 0

            try:
                cause_code = int(cause_code)
            except (ValueError, TypeError):
                cause_code = 0

            try:
                action = int(action)
            except (ValueError, TypeError):
                action = 0

            return {
                "fault_code": fault_code,
                "cause_code": cause_code,
                "action": action
            }
        except Exception as ex:
            print(f"{RED}[Excel Read Error]{RESET} {ex}")
            return {"fault_code": 0, "cause_code": 0, "action": 0}


def write_telemetry_to_excel(filepath: str, event_type: str, data: Dict[str, Any]) -> None:
    """Updates live telemetry cells in DATA TRANSFER (Rows 821-827) and saves."""
    if not openpyxl or not filepath or not os.path.isfile(filepath):
        return

    with excel_lock:
        try:
            wb = openpyxl.load_workbook(filepath, data_only=False)
            ws = wb["DATA TRANSFER"]

            fault_code = data.get("fault_code", 0)
            step_num = data.get("step_number", 0)
            total_steps = data.get("total_steps", 0)
            wrong_attempts = data.get("wrong_attempts", 0)
            is_completed = data.get("is_fault_completed", False)

            if event_type == "fault_started":
                ws.cell(row=821, column=6, value=fault_code)       # Active_Fault_Code (Integer)
                ws.cell(row=822, column=6, value=1)                # Current_Step_Number (Integer)
                ws.cell(row=823, column=6, value=total_steps)      # Total_Steps (Integer)
                ws.cell(row=824, column=6, value=0)                # Wrong_Attempts (Integer)
                ws.cell(row=825, column=6, value=0)                # Step_Accomplished (Boolean)
                ws.cell(row=826, column=6, value=0)                # Fault_Completed (Boolean)

                # Mark specific fault status row to 1 (Faults 101-116 map to contiguous Boolean Rows 827-842)
                if 101 <= fault_code <= 116:
                    target_row = 827 + (fault_code - 101)
                    ws.cell(row=target_row, column=6, value=1)

                ws.cell(row=843, column=6, value=0)                # Compression_Highlights_Active (0 when fault active)
                ws.cell(row=844, column=6, value=0)                # Arrows_Active (0 when fault active)
                ws.cell(row=854, column=6, value="fault_started")  # Telemetry_Event (String at Row 854 after all Booleans)

            elif event_type == "step_completed":
                ws.cell(row=821, column=6, value=fault_code)
                ws.cell(row=822, column=6, value=step_num)
                ws.cell(row=823, column=6, value=total_steps)
                ws.cell(row=824, column=6, value=wrong_attempts)
                ws.cell(row=825, column=6, value=1 if step_num > 0 else 0)  # Step finished pulse
                ws.cell(row=826, column=6, value=1 if is_completed else 0)
                ws.cell(row=843, column=6, value=1 if is_completed else 0)
                ws.cell(row=844, column=6, value=1 if is_completed else 0)
                ws.cell(row=854, column=6, value="step_completed")

            elif event_type == "fault_completed":
                ws.cell(row=821, column=6, value=fault_code)
                ws.cell(row=822, column=6, value=total_steps)
                ws.cell(row=823, column=6, value=total_steps)
                ws.cell(row=825, column=6, value=1)
                ws.cell(row=826, column=6, value=1)                # Fault finished!
                ws.cell(row=843, column=6, value=1)                # Compression highlights active
                ws.cell(row=844, column=6, value=1)                # Arrows active
                ws.cell(row=854, column=6, value="fault_completed")

            elif event_type == "fault_reset":
                ws.cell(row=821, column=6, value=0)
                ws.cell(row=822, column=6, value=0)
                ws.cell(row=823, column=6, value=0)
                ws.cell(row=824, column=6, value=0)
                ws.cell(row=825, column=6, value=0)
                ws.cell(row=826, column=6, value=0)
                for r in range(827, 843):
                    ws.cell(row=r, column=6, value=0)
                ws.cell(row=843, column=6, value=1)                # Compression highlights active
                ws.cell(row=844, column=6, value=1)                # Arrows active
                ws.cell(row=854, column=6, value="fault_reset")

            wb.save(filepath)
        except Exception as ex:
            # Excel might be locked if user opened it without sharing mode
            pass


def send_udp_command(payload: Dict[str, Any]) -> None:
    """Dispatches a JSON command to Unity UDPManager (Port 9000)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg_bytes = json.dumps(payload).encode("utf-8")
        sock.sendto(msg_bytes, (UNITY_IP, UNITY_COMMAND_PORT))
        sock.close()
    except Exception as ex:
        print(f"{RED}[Send Error]{RESET} {ex}")


def trigger_fault(fault_code: int) -> None:
    """Triggers a fault scenario."""
    title, steps = FAULT_CATALOG.get(fault_code, ("Custom Fault", 0))
    print(f"\n{YELLOW}>>> DISPATCHING TO UNITY (Port {UNITY_COMMAND_PORT}) >>>{RESET}")
    print(f"    Command:    {BOLD}trigger_fault{RESET}")
    print(f"    Fault Code: {CYAN}{fault_code}{RESET} ({title})")
    print(f"    Expected:   {steps} steps")

    payload = {
        "command": "trigger_fault",
        "fault_code": fault_code
    }
    send_udp_command(payload)


def reset_simulator() -> None:
    """Resets simulator to default idle state."""
    print(f"\n{YELLOW}>>> SENDING RESET COMMAND TO UNITY >>>{RESET}")
    payload = {"command": "reset"}
    send_udp_command(payload)


def toggle_compression_highlights(state: bool) -> None:
    """Explicitly turns compression highlights ON or OFF via JSON command."""
    print(f"\n{YELLOW}>>> TOGGLING COMPRESSION HIGHLIGHTS -> {BOLD}{state}{RESET} >>>")
    payload = {
        "command": "set_compression_highlights",
        "state": state
    }
    send_udp_command(payload)


def toggle_arrows(state: bool) -> None:
    """Explicitly turns idle arrows ON or OFF via JSON command."""
    print(f"\n{YELLOW}>>> TOGGLING ARROWS -> {BOLD}{state}{RESET} >>>")
    payload = {
        "command": "set_arrows",
        "state": state
    }
    send_udp_command(payload)


def telemetry_receiver_thread():
    """Background listener on port 5005 for telemetry from Unity."""
    global receiver_running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", TELEMETRY_LISTEN_PORT))
        sock.settimeout(1.0)
    except Exception as ex:
        print(f"{RED}[Telemetry Listener Bind Failed on {TELEMETRY_LISTEN_PORT}]: {ex}{RESET}")
        return

    print(f"{GREEN}[Telemetry Listener Active]{RESET} Listening on port {TELEMETRY_LISTEN_PORT} for Unity feedback...")

    while receiver_running:
        try:
            data, addr = sock.recvfrom(4096)
            if not data:
                continue

            text = data.decode("utf-8", errors="replace").strip()
            if not text:
                continue

            # Try parsing JSON
            if text.startswith("{") and text.endswith("}"):
                try:
                    payload = json.loads(text)
                    event_type = payload.get("event", "")

                    if event_type == "fault_started":
                        f_code = payload.get("fault_code", 0)
                        t_steps = payload.get("total_steps", 0)
                        title = FAULT_CATALOG.get(f_code, ("Scenario", 0))[0]
                        print(f"\n{CYAN}{'='*64}{RESET}")
                        print(f"{BOLD}{GREEN}★ [UNITY EVENT: FAULT STARTED] ★{RESET}")
                        print(f"  • Fault Code:   {CYAN}{f_code}{RESET} - {title}")
                        print(f"  • Total Steps:  {BOLD}{t_steps}{RESET}")
                        print(f"  • Status:       {GREEN}Active / Interactive{RESET}")
                        print(f"  {YELLOW}👉 Interact with tools in Unity now! Try correct tool or make mistakes.{RESET}")
                        print(f"{CYAN}{'='*64}{RESET}\n> ", end="", flush=True)

                        if active_excel_path:
                            write_telemetry_to_excel(active_excel_path, "fault_started", payload)

                    elif event_type == "step_completed":
                        f_code = payload.get("fault_code", 0)
                        s_num = payload.get("step_number", 0)
                        t_steps = payload.get("total_steps", 0)
                        wrong = payload.get("wrong_attempts", 0)
                        is_done = payload.get("is_fault_completed", False)

                        # Highlight mistakes
                        if wrong == 0:
                            mistake_str = f"{GREEN}0 (Clean First-Try!){RESET}"
                        elif wrong >= 3:
                            mistake_str = f"{YELLOW}{BOLD}{wrong} Mistakes (3 Strikes -> Auto-Demonstrated Step!){RESET}"
                        else:
                            mistake_str = f"{RED}{wrong} Wrong Tool Attempt(s)!{RESET}"

                        print(f"\n{CYAN}{'-'*64}{RESET}")
                        print(f"{BOLD}{GREEN}✔ [UNITY EVENT: STEP COMPLETED] Step {s_num} / {t_steps}{RESET}")
                        print(f"  • Fault Code:      {CYAN}{f_code}{RESET}")
                        print(f"  • Mistakes Count:  {mistake_str}")
                        print(f"  • Step Status:     {GREEN}Accomplished{RESET}")
                        print(f"  • Fault Finished?: {BOLD}{is_done}{RESET}")
                        print(f"{CYAN}{'-'*64}{RESET}\n> ", end="", flush=True)

                        if active_excel_path:
                            write_telemetry_to_excel(active_excel_path, "step_completed", payload)

                    elif event_type == "fault_completed":
                        f_code = payload.get("fault_code", 0)
                        t_steps = payload.get("total_steps", 0)
                        attempts_list = payload.get("wrong_attempts_per_step", [])
                        total_mistakes = sum(attempts_list) if attempts_list else 0

                        print(f"\n{GREEN}{'='*64}{RESET}")
                        print(f"{BOLD}{GREEN}🎉 [UNITY EVENT: FAULT PROCEDURE COMPLETED!] 🎉{RESET}")
                        print(f"  • Fault Code:       {CYAN}{f_code}{RESET}")
                        print(f"  • All Steps Done:   {BOLD}{t_steps} / {t_steps}{RESET}")
                        print(f"  • Total Mistakes:   {RED if total_mistakes > 0 else GREEN}{total_mistakes}{RESET}")
                        print(f"  • Mistakes by Step: {attempts_list}")
                        print(f"  • Procedure Result: {GREEN}{BOLD}PASSED / WORKFLOW FINISHED{RESET}")
                        print(f"{GREEN}{'='*64}{RESET}\n> ", end="", flush=True)

                        if active_excel_path:
                            write_telemetry_to_excel(active_excel_path, "fault_completed", payload)

                    elif event_type == "compression_highlights_changed":
                        state = payload.get("compression_highlights", False)
                        st_str = f"{GREEN}ON / VISIBLE{RESET}" if state else f"{RED}OFF / HIDDEN{RESET}"
                        print(f"\n{MAGENTA}[UNITY EVENT: COMPRESSION HIGHLIGHTS CHANGED]{RESET} State: {st_str}\n> ", end="", flush=True)

                    elif event_type == "arrows_changed":
                        state = payload.get("arrows_active", False)
                        st_str = f"{GREEN}ON / VISIBLE{RESET}" if state else f"{RED}OFF / HIDDEN{RESET}"
                        print(f"\n{MAGENTA}[UNITY EVENT: ARROWS VISIBILITY CHANGED]{RESET} State: {st_str}\n> ", end="", flush=True)

                    elif event_type == "fault_reset":
                        print(f"\n{CYAN}[UNITY EVENT: FAULT RESET]{RESET} Simulator returned to Idle State (Highlights & Arrows: {GREEN}ON{RESET})\n> ", end="", flush=True)
                        if active_excel_path:
                            write_telemetry_to_excel(active_excel_path, "fault_reset", payload)

                    else:
                        print(f"\n{MAGENTA}[Unity JSON Telemetry]:{RESET} {payload}\n> ", end="", flush=True)

                except json.JSONDecodeError:
                    print(f"\n{YELLOW}[Unity Raw Telemetry]:{RESET} {text}\n> ", end="", flush=True)
            else:
                # Raw string (e.g. step number echo or csv)
                if text.isdigit():
                    print(f"\n{GREEN}[Unity Step Progress Pulse]: Step {text}{RESET}\n> ", end="", flush=True)
                else:
                    # Sliders echo
                    pass

        except socket.timeout:
            continue
        except Exception as ex:
            if receiver_running:
                print(f"\n{RED}[Receiver Error]: {ex}{RESET}\n> ", end="", flush=True)

    sock.close()


def print_menu():
    print(f"\n{CYAN}=================================================================={RESET}")
    print(f"{BOLD}   DS3D-HVAC Fault Management & Telemetry Test Console{RESET}")
    print(f"{CYAN}=================================================================={RESET}")
    print(f" Target Unity Address: {BOLD}{UNITY_IP}:{UNITY_COMMAND_PORT}{RESET}")
    print(f" Telemetry Inbound:    {BOLD}Port {TELEMETRY_LISTEN_PORT}{RESET}")
    if active_excel_path:
        print(f" Linked Excel:         {GREEN}{os.path.basename(active_excel_path)}{RESET}")
    else:
        print(f" Linked Excel:         {YELLOW}None (Live standalone mode){RESET}")
    print(f"{CYAN}------------------------------------------------------------------{RESET}")
    print(f" {BOLD}COMMANDS:{RESET}")
    print(f"   {GREEN}[101 - 114]{RESET}  : Trigger Fault Scenario (e.g. 101, 102, 107...)")
    print(f"   {GREEN}e / excel{RESET}    : Read Instructor Fault & Cause from Excel and trigger")
    print(f"   {GREEN}r / reset{RESET}    : Reset Unity Simulator (sends JSON reset prompt)")
    print(f"   {GREEN}hon / hoff{RESET}   : Explicitly turn Compression Highlights ON / OFF")
    print(f"   {GREEN}aon / aoff{RESET}   : Explicitly turn Idle Arrows ON / OFF")
    print(f"   {GREEN}l / list{RESET}     : Display Full Catalog of all 14 Fault Scenarios")
    print(f"   {GREEN}q / quit{RESET}     : Exit Test Bridge")
    print(f"{CYAN}=================================================================={RESET}\n")


def print_catalog():
    print(f"\n{BOLD}{CYAN}Available Fault Scenarios in HVAC Unity Simulator:{RESET}")
    print(f"{'Code':<6} | {'Steps':<6} | {'Fault Title':<45}")
    print("-" * 65)
    for code, (title, steps) in FAULT_CATALOG.items():
        if code <= 114:
            print(f"{CYAN}{code:<6}{RESET} | {steps:<6} | {title:<45}")
    print("-" * 65)


def main():
    global active_excel_path, receiver_running

    # Enable ANSI colors on Windows
    os.system("")

    active_excel_path = find_excel_file()

    # Start background receiver thread
    t = threading.Thread(target=telemetry_receiver_thread, daemon=True)
    t.start()
    time.sleep(0.3)

    # Check CLI arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().strip()
        if arg in ["--excel", "-e"]:
            if active_excel_path:
                info = read_trigger_from_excel(active_excel_path)
                f_code = info["fault_code"]
                if f_code in FAULT_CATALOG:
                    trigger_fault(f_code)
                else:
                    print(f"{YELLOW}Excel row F1209 has Fault Code = {f_code} (Defaulting to 101){RESET}")
                    trigger_fault(101)
            else:
                print(f"{RED}No Excel file found!{RESET}")
        elif arg.isdigit() and int(arg) in FAULT_CATALOG:
            trigger_fault(int(arg))

    print_menu()

    while True:
        try:
            cmd = input("> ").strip().lower()
            if not cmd:
                continue

            if cmd in ["q", "quit", "exit"]:
                print(f"{YELLOW}Shutting down test bridge...{RESET}")
                receiver_running = False
                break

            elif cmd in ["e", "excel"]:
                if not active_excel_path:
                    print(f"{RED}Excel file not found.{RESET}")
                    continue
                info = read_trigger_from_excel(active_excel_path)
                f_code = info["fault_code"]
                c_code = info["cause_code"]
                action = info["action"]
                print(f"{CYAN}[Excel Read]{RESET} Fault: {f_code}, Cause: {c_code}, Action: {action}")
                if action == 2:
                    reset_simulator()
                # elif action == 3:
                #     skip_step()
                elif f_code in FAULT_CATALOG:
                    trigger_fault(f_code)
                else:
                    print(f"{YELLOW}No valid fault code set in Excel F1209 (value was: {f_code}). Triggering 101...{RESET}")
                    trigger_fault(101)

            elif cmd in ["r", "reset"]:
                reset_simulator()

            elif cmd in ["hon", "h_on", "highlight_on"]:
                toggle_compression_highlights(True)

            elif cmd in ["hoff", "h_off", "highlight_off"]:
                toggle_compression_highlights(False)

            elif cmd in ["aon", "a_on", "arrow_on", "arrows_on"]:
                toggle_arrows(True)

            elif cmd in ["aoff", "a_off", "arrow_off", "arrows_off"]:
                toggle_arrows(False)

            elif cmd in ["l", "list"]:
                print_catalog()

            elif cmd.isdigit():
                code = int(cmd)
                if code in FAULT_CATALOG:
                    trigger_fault(code)
                else:
                    print(f"{RED}Unknown fault code: {code}. Type 'list' to see available codes.{RESET}")

            else:
                print(f"{RED}Unknown command: '{cmd}'. Type 'list' or a fault number (e.g. 101).{RESET}")

        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Exiting...{RESET}")
            receiver_running = False
            break


if __name__ == "__main__":
    main()
