"""
DS3D-HVAC — Telemetry Test Bench & Live 20ms Streaming Dashboard
================================================================
Automated real-time bidirectional UDP telemetry bridge for Unity HVAC Simulator.
Loads HVAC variable Excel sheets, generates compliant JSON/CSV payloads,
streams control packets to Unity (Port 9000), and receives telemetry on Port 5005.
"""

import json
import socket
import threading
import time
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


HVAC_SPEED_VARS = [
    ("BlueArrowOut", "Blue Arrow Airflow"),
    ("Fan1", "Condenser Fan 1"),
    ("Fan2", "Condenser Fan 2"),
    ("GreenArrowIN1", "Fresh Air Inlet 1"),
    ("GreenArrowIN2", "Fresh Air Inlet 2"),
    ("YellowArrowIn", "Return Airflow")
]

HVAC_COLOR_VARS = [
    ("RedArrow_Inlet", "Hot Air Inlet (Color)"),
    ("RedArrow_Outlet", "Hot Air Outlet (Color)"),
    ("BlueArrow_Outlet", "Cool Air Outlet (Color)"),
    ("GreenArrow_Inlet", "Fresh Air Inlet (Color)"),
    ("YellowArrow_Inlet", "Return Air Inlet (Color)")
]

HVAC_DAMPER_VARS = [
    ("FADL", "Fresh Air Damper Left"),
    ("FADR", "Fresh Air Damper Right"),
    ("RAD", "Return Air Damper")
]

HVAC_BOOLEAN_VARS = [
    ("ShowHideObjects", "Show / Hide Objects"),
    ("Application Quit", "Application Quit Trigger")
]


class HVACTelemetryDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DS3D-HVAC Telemetry & JSON Verification Test Bench")
        self.geometry("1060x820")
        self.configure(bg="#f0f2f5")

        self.sender_ip = tk.StringVar(value="127.0.0.1")
        self.sender_port = tk.IntVar(value=9000)
        self.receiver_ip = tk.StringVar(value="127.0.0.1")
        self.receiver_port = tk.IntVar(value=5005)

        # 20ms streaming configuration (50 Hz)
        self.is_streaming_tx = tk.BooleanVar(value=False)
        self.stream_interval_ms = tk.IntVar(value=50)
        self.payload_format = tk.StringVar(value="JSON")  # "JSON" or "CSV"

        self.is_running = False
        self.rx_socket = None
        self.tx_socket = None
        self.rx_thread = None
        self.tx_thread = None

        self.tx_count = 0
        self.rx_count = 0

        # UI Variables
        self.speed_vars = {name: tk.DoubleVar(value=5.0) for name, _ in HVAC_SPEED_VARS}
        self.color_vars = {name: tk.DoubleVar(value=5.0) for name, _ in HVAC_COLOR_VARS}
        self.damper_vars = {name: tk.DoubleVar(value=0.0) for name, _ in HVAC_DAMPER_VARS}
        self.bool_vars = {name: tk.BooleanVar(value=False) for name, _ in HVAC_BOOLEAN_VARS}

        self.create_widgets()

        # Start network listener
        self.after(150, self.start_network)

    def create_widgets(self):
        # 1. Header Banner
        header = tk.Frame(self, bg="#00695c", height=50)
        header.pack(fill=tk.X)
        lbl_title = tk.Label(header, text="DS3D-HVAC TELEMETRY TEST BENCH (UDP & EXCEL)", font=("Segoe UI", 15, "bold"), fg="white", bg="#00695c")
        lbl_title.pack(side=tk.LEFT, padx=15, pady=8)

        self.lbl_stats = tk.Label(header, text="TX: 0 pkts | RX: 0 pkts", font=("Consolas", 10, "bold"), fg="#80cbc4", bg="#00695c")
        self.lbl_stats.pack(side=tk.RIGHT, padx=15, pady=12)

        # 2. Connection & Rate Config Bar
        cfg_frame = tk.LabelFrame(self, text="Network & Auto-Stream Settings", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        cfg_frame.pack(fill=tk.X, padx=12, pady=6)

        tk.Label(cfg_frame, text="Target IP:").grid(row=0, column=0, padx=2)
        tk.Entry(cfg_frame, textvariable=self.sender_ip, width=10).grid(row=0, column=1, padx=2)

        tk.Label(cfg_frame, text="Unity Port:").grid(row=0, column=2, padx=2)
        tk.Entry(cfg_frame, textvariable=self.sender_port, width=5).grid(row=0, column=3, padx=2)

        tk.Label(cfg_frame, text="Listen Port:").grid(row=0, column=4, padx=2)
        tk.Entry(cfg_frame, textvariable=self.receiver_port, width=5).grid(row=0, column=5, padx=2)

        tk.Label(cfg_frame, text="Interval (ms):").grid(row=0, column=6, padx=4)
        tk.Spinbox(cfg_frame, from_=5, to=500, increment=5, textvariable=self.stream_interval_ms, width=5).grid(row=0, column=7, padx=2)

        chk_stream = tk.Checkbutton(cfg_frame, text="Auto-Stream", variable=self.is_streaming_tx, font=("Segoe UI", 9, "bold"), fg="#004d40")
        chk_stream.grid(row=0, column=8, padx=8)

        tk.Label(cfg_frame, text="Format:").grid(row=0, column=9, padx=2)
        ttk.Combobox(cfg_frame, textvariable=self.payload_format, values=["JSON", "CSV"], width=6, state="readonly").grid(row=0, column=10, padx=2)

        # 3. Sliders Area (Scrollable or Tabbed)
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=False, padx=12, pady=4)

        # Tab 1: Speeds & Airflow (6 parameters)
        tab_speed = ttk.Frame(notebook, padding=10)
        notebook.add(tab_speed, text="1. Speeds & Airflow (6)")
        self.build_slider_grid(tab_speed, HVAC_SPEED_VARS, self.speed_vars, 0.0, 10.0)

        # Tab 2: Colors & Temperatures (5 parameters)
        tab_color = ttk.Frame(notebook, padding=10)
        notebook.add(tab_color, text="2. Color Intensities (5)")
        self.build_slider_grid(tab_color, HVAC_COLOR_VARS, self.color_vars, 0.0, 10.0)

        # Tab 3: Dampers & BlendShapes (3 parameters)
        tab_damper = ttk.Frame(notebook, padding=10)
        notebook.add(tab_damper, text="3. Dampers / BlendShapes (3)")
        self.build_slider_grid(tab_damper, HVAC_DAMPER_VARS, self.damper_vars, 0.0, 10.0)

        # Tab 4: Booleans & Controls (2 toggles)
        tab_bool = ttk.Frame(notebook, padding=10)
        notebook.add(tab_bool, text="4. System Toggles (2)")
        for idx, (var_name, label_text) in enumerate(HVAC_BOOLEAN_VARS):
            chk = tk.Checkbutton(tab_bool, text=f"{var_name} — ({label_text})", variable=self.bool_vars[var_name], font=("Segoe UI", 10, "bold"))
            chk.pack(anchor=tk.W, pady=8, padx=20)

        # 4. Action Buttons Bar
        btn_frame = tk.Frame(self, pady=4)
        btn_frame.pack(fill=tk.X, padx=12)

        btn_load_excel = tk.Button(btn_frame, text="📂 Load Excel Sheet...", command=self.load_excel, bg="#00796b", fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        btn_load_excel.pack(side=tk.LEFT, padx=4)

        btn_send = tk.Button(btn_frame, text="🚀 Send Single Packet", command=self.send_single_payload, bg="#00897b", fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        btn_send.pack(side=tk.LEFT, padx=4)

        btn_reset = tk.Button(btn_frame, text="↺ Reset Defaults", command=self.reset_defaults, bg="#78909c", fg="white", font=("Segoe UI", 9, "bold"), padx=8, pady=4)
        btn_reset.pack(side=tk.LEFT, padx=4)

        btn_clear = tk.Button(btn_frame, text="Clear RX Log", command=lambda: self.txt_receive.delete("1.0", tk.END), bg="#b0bec5", fg="black", font=("Segoe UI", 9), padx=8, pady=4)
        btn_clear.pack(side=tk.RIGHT, padx=4)

        # 5. Live Telemetry Viewers (TX & RX)
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        frame_tx = tk.LabelFrame(paned, text="Outgoing Packet (JSON / CSV Sent)", font=("Segoe UI", 9, "bold"), padx=6, pady=4)
        self.txt_send = tk.Text(frame_tx, height=12, width=50, font=("Consolas", 9), bg="#fafafa")
        self.txt_send.pack(fill=tk.BOTH, expand=True)
        paned.add(frame_tx)

        frame_rx = tk.LabelFrame(paned, text="Incoming Telemetry Feedback (Port 5005)", font=("Segoe UI", 9, "bold"), padx=6, pady=4)
        self.txt_receive = tk.Text(frame_rx, height=12, width=50, font=("Consolas", 9), bg="#263238", fg="#aeea00")
        self.txt_receive.pack(fill=tk.BOTH, expand=True)
        paned.add(frame_rx)

    def build_slider_grid(self, parent, var_list, data_dict, min_val, max_val):
        for idx, (name, label_text) in enumerate(var_list):
            row = idx // 2
            col = (idx % 2) * 3

            lbl = tk.Label(parent, text=f"{name}:", font=("Segoe UI", 9, "bold"), anchor="w", width=18)
            lbl.grid(row=row, column=col, sticky="w", padx=6, pady=4)

            slider = tk.Scale(parent, from_=min_val, to=max_val, resolution=0.1, orient=tk.HORIZONTAL, variable=data_dict[name], length=200)
            slider.grid(row=row, column=col+1, padx=4, pady=4)

            val_lbl = tk.Label(parent, textvariable=data_dict[name], font=("Consolas", 9), width=5)
            val_lbl.grid(row=row, column=col+2, padx=4, pady=4)

    def reset_defaults(self):
        for name, _ in HVAC_SPEED_VARS: self.speed_vars[name].set(5.0)
        for name, _ in HVAC_COLOR_VARS: self.color_vars[name].set(5.0)
        for name, _ in HVAC_DAMPER_VARS: self.damper_vars[name].set(0.0)
        for name, _ in HVAC_BOOLEAN_VARS: self.bool_vars[name].set(False)

    def build_json_payload(self):
        speed_list = [{"Name": name, "Value": round(self.speed_vars[name].get(), 2)} for name, _ in HVAC_SPEED_VARS]
        amp_list = (
            [{"Name": name, "Value": round(self.color_vars[name].get(), 2)} for name, _ in HVAC_COLOR_VARS] +
            [{"Name": name, "Value": round(self.damper_vars[name].get(), 2)} for name, _ in HVAC_DAMPER_VARS]
        )
        bool_list = [{"Name": name, "Value": self.bool_vars[name].get()} for name, _ in HVAC_BOOLEAN_VARS]

        payload = {
            "Hvac": {
                "Speed": speed_list,
                "Amplitude": amp_list,
                "Boolean": bool_list
            }
        }
        return json.dumps(payload, separators=(',', ':'))

    def build_csv_payload(self):
        tokens = []
        for name, _ in HVAC_SPEED_VARS: tokens.append(f"{self.speed_vars[name].get():.1f}")
        for name, _ in HVAC_COLOR_VARS: tokens.append(f"{self.color_vars[name].get():.1f}")
        for name, _ in HVAC_DAMPER_VARS: tokens.append(f"{self.damper_vars[name].get():.1f}")
        for name, _ in HVAC_BOOLEAN_VARS: tokens.append("1" if self.bool_vars[name].get() else "0")
        return ",".join(tokens)

    def start_network(self):
        if self.is_running: return
        self.is_running = True

        # RX Socket
        try:
            self.rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.rx_socket.bind(("0.0.0.0", self.receiver_port.get()))
            self.rx_socket.settimeout(0.2)
            self.rx_thread = threading.Thread(target=self.rx_loop, daemon=True)
            self.rx_thread.start()
        except Exception as e:
            self.txt_receive.insert("1.0", f"[WARN] Could not bind RX port {self.receiver_port.get()}: {e}\n")

        # TX Socket
        try:
            self.tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.tx_thread = threading.Thread(target=self.tx_stream_loop, daemon=True)
            self.tx_thread.start()
        except Exception as e:
            pass

    def tx_stream_loop(self):
        t_last_display = 0.0
        while self.is_running:
            t_start = time.perf_counter()
            if self.is_streaming_tx.get():
                try:
                    payload = self.build_json_payload() if self.payload_format.get() == "JSON" else self.build_csv_payload()
                    dest = (self.sender_ip.get(), self.sender_port.get())
                    if self.tx_socket:
                        self.tx_socket.sendto(payload.encode("utf-8"), dest)
                        self.tx_count += 1

                    now = time.time()
                    if now - t_last_display > 0.2:
                        t_last_display = now
                        self.after(0, lambda p=payload: self.update_tx_display(p))
                except Exception:
                    pass

            interval_sec = max(0.005, self.stream_interval_ms.get() / 1000.0)
            elapsed = time.perf_counter() - t_start
            time.sleep(max(0.0, interval_sec - elapsed))

    def rx_loop(self):
        while self.is_running:
            try:
                data, addr = self.rx_socket.recvfrom(8192)
                if data:
                    self.rx_count += 1
                    text = data.decode("utf-8", errors="ignore")
                    now = time.strftime("%H:%M:%S")
                    msg = f"[{now}] From {addr} ({len(data)} B):\n{text}\n\n"
                    self.after(0, lambda m=msg: self.update_rx_display(m))
            except socket.timeout:
                continue
            except Exception:
                break

    def update_tx_display(self, payload):
        self.txt_send.delete("1.0", tk.END)
        self.txt_send.insert(tk.END, payload)
        self.lbl_stats.configure(text=f"TX: {self.tx_count} pkts | RX: {self.rx_count} pkts")

    def update_rx_display(self, text):
        self.txt_receive.insert("1.0", text)

    def send_single_payload(self):
        payload = self.build_json_payload() if self.payload_format.get() == "JSON" else self.build_csv_payload()
        try:
            tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tx.sendto(payload.encode("utf-8"), (self.sender_ip.get(), self.sender_port.get()))
            tx.close()
            self.tx_count += 1
            self.update_tx_display(payload)
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send: {e}")

    def load_excel(self):
        if not HAS_OPENPYXL:
            messagebox.showerror("Missing Library", "openpyxl is required to load Excel sheets.\nRun: pip install openpyxl")
            return

        candidates = [
            r"C:\Users\user\Downloads\hvactest.xlsx",
            r"C:\Users\user\Downloads\DS3D_HVAC_Variable_List.xlsx",
            os.path.join(os.path.dirname(__file__), "DS3D_HVAC_Variable_List.xlsx")
        ]
        excel_path = next((p for p in candidates if os.path.exists(p)), None)

        if not excel_path:
            excel_path = filedialog.askopenfilename(
                title="Select HVAC Variable Excel Sheet",
                filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
            )

        if not excel_path: return

        try:
            wb = openpyxl.load_workbook(excel_path, data_only=True)
            ws = wb.active
            loaded = 0

            # Scan rows
            for r in range(1, ws.max_row + 1):
                for c in range(1, ws.max_column + 1):
                    val = ws.cell(r, c).value
                    if val and isinstance(val, str):
                        cleaned = val.strip()

                        # Collect row numbers
                        row_vals = [ws.cell(r, col).value for col in range(1, ws.max_column + 1)]
                        candidate_nums = []
                        for col_idx, cv in enumerate(row_vals):
                            if col_idx == c - 1: continue
                            if isinstance(cv, (int, float)) and cv is not None:
                                candidate_nums.append((col_idx + 1, cv))
                            elif isinstance(cv, str) and cv.strip().lower() in ("true", "false", "0", "1"):
                                candidate_nums.append((col_idx + 1, 1.0 if cv.strip().lower() in ("true", "1") else 0.0))

                        # Exclude col 1 (SR.No)
                        filtered = [cn for cn in candidate_nums if cn[0] > 1]
                        num_val = float(filtered[0][1]) if filtered else 5.0

                        for name, _ in HVAC_SPEED_VARS:
                            if cleaned.lower() == name.lower():
                                self.speed_vars[name].set(num_val); loaded += 1; break
                        for name, _ in HVAC_COLOR_VARS:
                            if cleaned.lower() == name.lower():
                                self.color_vars[name].set(num_val); loaded += 1; break
                        for name, _ in HVAC_DAMPER_VARS:
                            if cleaned.lower() == name.lower():
                                self.damper_vars[name].set(num_val); loaded += 1; break
                        for name, _ in HVAC_BOOLEAN_VARS:
                            if cleaned.lower() == name.lower():
                                self.bool_vars[name].set(num_val > 0.5); loaded += 1; break

            payload = self.build_json_payload()
            self.update_tx_display(payload)
            messagebox.showinfo("Excel Loaded", f"Successfully loaded {loaded} HVAC parameters from:\n{os.path.basename(excel_path)}")
        except Exception as e:
            messagebox.showerror("Excel Error", f"Failed to load Excel: {e}")


if __name__ == "__main__":
    app = HVACTelemetryDashboard()
    app.mainloop()
