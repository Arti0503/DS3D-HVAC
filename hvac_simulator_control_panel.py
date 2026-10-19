"""
DS3D-HVAC — Interactive Simulation & Telemetry Control Panel
============================================================
A graphical test bench aligned with the final Excel specification
(J886_Software_HVAC_phase1-V1_updated_19-Oct 3pm.xlsx / Unity_DS3D_Tables_Exact.xlsx).

Allows interactive manual testing of:
1. Fault Triggering (Faults 101-114, Causes 1-5, Reset)
2. Step Fast-Forwarding ('skip' command) & Live Mistake / Step Tracking
3. Sensor Highlights (FAT, RAT, SAT, Smoke Detector)
4. Compressor Highlights (Compressors 1-4)
5. Physical Damper Positions (FADL, FADR, RAD BlendShapes 0-100%)
6. Airflow Speeds & Material Colors
7. Show/Hide Casing Panels & Application Quit (DS3D_OFF)
8. Real-time Live UDP Telemetry Feed on Port 5005
"""

import socket
import json
import threading
import time
import subprocess
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

UNITY_IP = "127.0.0.1"
UNITY_RX_PORT = 9000
LABVIEW_LISTEN_PORT = 5005
BUILD_EXE = r"C:\Github_Projects\Hvac_Builds\HVAC_V6\DS3D_HVAC.exe"

FAULTS_DATA = [
    (101, "No HVAC operations", 16),
    (102, "No ventilation", 22),
    (103, "Reduced ventilation", 17),
    (104, "Suction low and discharge low (C1)", 15),
    (105, "Suction low and discharge low (C2)", 14),
    (106, "High suction and high discharge", 26),
    (107, "Compressor not operating", 40),
    (108, "Reduced cooling", 33),
    (109, "No Heating", 15),
    (110, "Over Cooling", 8),
    (111, "Over Heating", 7),
    (112, "No emergency ventilation", 14),
    (113, "Smoke identified in saloon", 15),
    (114, "Compressor / Blower noisy", 36)
]

SPEED_PARAMS = [
    ("BlueArrowOut", "Blue Arrow (Fresh Air)"),
    ("Fan1", "Condenser Fan 1"),
    ("Fan2", "Evaporator Fan 2"),
    ("GreenArrowIN1", "Fresh Air Damper Right"),
    ("GreenArrowIN2", "Fresh Air Damper Left"),
    ("YellowArrowIn", "Return Air Damper")
]

COLOR_PARAMS = [
    ("RedArrow_Inlet", "Hot Air Inlet (Red/Color)"),
    ("RedArrow_Outlet", "Condenser Fan Red Arrow"),
    ("BlueArrow_Outlet", "Evaporator Fan Cool Arrow"),
    ("GreenArrow_Inlet", "Fresh Air Inlet Intensity"),
    ("YellowArrow_Inlet", "Return Air Inlet Intensity")
]

DAMPER_PARAMS = [
    ("FADL", "Fresh Air Damper Left (0-100%)"),
    ("FADR", "Fresh Air Damper Right (0-100%)"),
    ("RAD", "Return Air Damper (0-100%)")
]


class HVACControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DS3D-HVAC Simulation & Telemetry Interactive Control Panel")
        self.geometry("1240x840")
        self.minsize(1050, 720)
        self.configure(bg="#1e1e2e")

        # Network state
        self.sock_rx = None
        self.rx_thread = None
        self.is_running = True
        self.tx_count = 0
        self.rx_count = 0

        # Simulation status tracking
        self.active_fault_code = 0
        self.current_step = 0
        self.total_steps = 0
        self.total_mistakes = 0
        self.is_completed = False

        # Widget state variables
        self.selected_fault = tk.StringVar(value="101: No HVAC operations (16 steps)")
        self.selected_cause = tk.IntVar(value=1)
        
        # Highlights & Toggles
        self.var_comp1 = tk.BooleanVar(value=True)
        self.var_comp2 = tk.BooleanVar(value=True)
        self.var_comp3 = tk.BooleanVar(value=True)
        self.var_comp4 = tk.BooleanVar(value=True)
        
        self.var_fat_sensor = tk.BooleanVar(value=True)
        self.var_rat_sensor = tk.BooleanVar(value=True)
        self.var_sat_sensor = tk.BooleanVar(value=True)
        self.var_smoke_sensor = tk.BooleanVar(value=True)
        
        self.var_show_hide = tk.BooleanVar(value=False)
        self.var_arrows = tk.BooleanVar(value=True)
        self.var_comp_master = tk.BooleanVar(value=True)

        # Continuous Sliders
        self.speed_vars = {k: tk.DoubleVar(value=5.0) for k, _ in SPEED_PARAMS}
        self.color_vars = {k: tk.DoubleVar(value=0.0) for k, _ in COLOR_PARAMS}
        self.damper_vars = {k: tk.DoubleVar(value=0.0) for k, _ in DAMPER_PARAMS}

        self.apply_theme()
        self.build_ui()
        self.start_network()

    def apply_theme(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Catppuccin-inspired dark palette
        self.c_bg = "#1e1e2e"
        self.c_card = "#252538"
        self.c_accent = "#89b4fa"
        self.c_green = "#a6e3a1"
        self.c_red = "#f38ba8"
        self.c_yellow = "#f9e2af"
        self.c_text = "#cdd6f4"
        self.c_subtext = "#a6adc8"
        self.c_border = "#313244"

        self.style.configure(".", background=self.c_bg, foreground=self.c_text, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=self.c_bg)
        self.style.configure("Card.TFrame", background=self.c_card, relief="flat")
        self.style.configure("TLabel", background=self.c_bg, foreground=self.c_text)
        self.style.configure("Card.TLabel", background=self.c_card, foreground=self.c_text)
        self.style.configure("CardHeader.TLabel", background=self.c_card, foreground=self.c_accent, font=("Segoe UI", 11, "bold"))
        self.style.configure("TNotebook", background=self.c_bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=self.c_card, foreground=self.c_text, padding=[12, 6], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", self.c_accent)], foreground=[("selected", "#11111b")])

    def build_ui(self):
        # 1. Header Bar
        header = tk.Frame(self, bg="#181825", height=60)
        header.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(header, text="DS3D-HVAC SIMULATION TEST BENCH", font=("Segoe UI", 14, "bold"), fg=self.c_accent, bg="#181825")
        title_lbl.pack(side=tk.LEFT, padx=16, pady=10)

        subtitle_lbl = tk.Label(header, text="(Excel Interface & Telemetry Verification)", font=("Segoe UI", 10), fg=self.c_subtext, bg="#181825")
        subtitle_lbl.pack(side=tk.LEFT, padx=4, pady=12)

        self.lbl_net_status = tk.Label(header, text="● UDP LISTENING (Port 5005)", font=("Consolas", 10, "bold"), fg=self.c_green, bg="#181825")
        self.lbl_net_status.pack(side=tk.RIGHT, padx=16, pady=12)

        self.lbl_tx_rx = tk.Label(header, text="TX: 0 | RX: 0", font=("Consolas", 10), fg=self.c_subtext, bg="#181825")
        self.lbl_tx_rx.pack(side=tk.RIGHT, padx=12, pady=12)

        # 2. Main Layout (Left: Controls, Right: Live Log)
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=self.c_border, sashwidth=4, bd=0)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left_container = tk.Frame(main_paned, bg=self.c_bg)
        right_container = tk.Frame(main_paned, bg=self.c_bg)

        main_paned.add(left_container, width=680)
        main_paned.add(right_container, width=540)

        # --- LEFT: STATUS CARDS + TABS ---
        self.build_status_cards(left_container)

        notebook = ttk.Notebook(left_container)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        tab_faults = ttk.Frame(notebook)
        tab_highlights = ttk.Frame(notebook)
        tab_sliders = ttk.Frame(notebook)
        tab_system = ttk.Frame(notebook)

        notebook.add(tab_faults, text=" ⚡ Fault Management ")
        notebook.add(tab_highlights, text=" 💡 Component Highlights ")
        notebook.add(tab_sliders, text=" 🎛️ Speeds & Dampers ")
        notebook.add(tab_system, text=" ⚙️ System & Build ")

        self.build_tab_faults(tab_faults)
        self.build_tab_highlights(tab_highlights)
        self.build_tab_sliders(tab_sliders)
        self.build_tab_system(tab_system)

        # --- RIGHT: LIVE TELEMETRY TERMINAL ---
        self.build_telemetry_terminal(right_container)

    def build_status_cards(self, parent):
        card_frame = tk.Frame(parent, bg=self.c_card, padx=12, pady=10)
        card_frame.pack(fill=tk.X)

        # Badge 1: Fault Status
        f1 = tk.Frame(card_frame, bg=self.c_card)
        f1.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        tk.Label(f1, text="ACTIVE FAULT", font=("Segoe UI", 9, "bold"), fg=self.c_subtext, bg=self.c_card).pack(anchor="w")
        self.lbl_active_fault = tk.Label(f1, text="IDLE", font=("Segoe UI", 12, "bold"), fg=self.c_text, bg=self.c_card)
        self.lbl_active_fault.pack(anchor="w")

        # Badge 2: Step Counter
        f2 = tk.Frame(card_frame, bg=self.c_card)
        f2.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        tk.Label(f2, text="CURRENT STEP", font=("Segoe UI", 9, "bold"), fg=self.c_subtext, bg=self.c_card).pack(anchor="w")
        self.lbl_step_counter = tk.Label(f2, text="0 / 0", font=("Segoe UI", 12, "bold"), fg=self.c_accent, bg=self.c_card)
        self.lbl_step_counter.pack(anchor="w")

        # Badge 3: Mistakes
        f3 = tk.Frame(card_frame, bg=self.c_card)
        f3.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        tk.Label(f3, text="MISTAKES", font=("Segoe UI", 9, "bold"), fg=self.c_subtext, bg=self.c_card).pack(anchor="w")
        self.lbl_mistakes = tk.Label(f3, text="0", font=("Segoe UI", 12, "bold"), fg=self.c_yellow, bg=self.c_card)
        self.lbl_mistakes.pack(anchor="w")

        # Badge 4: Completion State
        f4 = tk.Frame(card_frame, bg=self.c_card)
        f4.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        tk.Label(f4, text="COMPLETION", font=("Segoe UI", 9, "bold"), fg=self.c_subtext, bg=self.c_card).pack(anchor="w")
        self.lbl_completed = tk.Label(f4, text="NOT COMPLETED", font=("Segoe UI", 10, "bold"), fg=self.c_subtext, bg=self.c_card)
        self.lbl_completed.pack(anchor="w")

    def build_tab_faults(self, parent):
        container = tk.Frame(parent, bg=self.c_bg, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. Fault Selection Box
        box_sel = tk.LabelFrame(container, text=" Fault Selection (Excel Spec 101–114) ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=10)
        box_sel.pack(fill=tk.X, pady=(0, 10))

        fault_options = [f"{f[0]}: {f[1]} ({f[2]} steps)" for f in FAULTS_DATA]
        cb_fault = ttk.Combobox(box_sel, textvariable=self.selected_fault, values=fault_options, state="readonly", font=("Segoe UI", 10), width=45)
        cb_fault.pack(fill=tk.X, pady=4)

        row_cause = tk.Frame(box_sel, bg=self.c_card)
        row_cause.pack(fill=tk.X, pady=6)
        tk.Label(row_cause, text="Trigger Cause:", font=("Segoe UI", 10), fg=self.c_text, bg=self.c_card).pack(side=tk.LEFT, padx=(0, 8))
        for c in [1, 2, 3, 4]:
            tk.Radiobutton(row_cause, text=f"Cause {c}", variable=self.selected_cause, value=c, bg=self.c_card, fg=self.c_text, selectcolor=self.c_border, activebackground=self.c_card).pack(side=tk.LEFT, padx=6)

        # 2. Main Action Buttons
        box_actions = tk.LabelFrame(container, text=" Commands (Sent to Unity Port 9000) ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=12)
        box_actions.pack(fill=tk.X, pady=(0, 10))

        btn_grid = tk.Frame(box_actions, bg=self.c_card)
        btn_grid.pack(fill=tk.X)

        btn_trigger = tk.Button(btn_grid, text="🚀 TRIGGER FAULT", font=("Segoe UI", 11, "bold"), bg="#2e7d32", fg="white", activebackground="#388e3c", relief="flat", padx=14, pady=10, command=self.cmd_trigger_fault)
        btn_trigger.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        btn_skip = tk.Button(btn_grid, text="⏩ NEXT STEP (SKIP)", font=("Segoe UI", 11, "bold"), bg="#1565c0", fg="white", activebackground="#1976d2", relief="flat", padx=14, pady=10, command=self.cmd_skip_step)
        btn_skip.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        btn_reset = tk.Button(btn_grid, text="🔄 RESET FAULT", font=("Segoe UI", 11, "bold"), bg="#c62828", fg="white", activebackground="#d32f2f", relief="flat", padx=14, pady=10, command=self.cmd_reset_fault)
        btn_reset.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        # 3. Quick Fault Trigger Grid (Buttons 101 to 114)
        box_quick = tk.LabelFrame(container, text=" Quick One-Click Fault Triggers ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=10, pady=10)
        box_quick.pack(fill=tk.BOTH, expand=True)

        grid_frame = tk.Frame(box_quick, bg=self.c_card)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        for idx, (code, name, steps) in enumerate(FAULT_DATA := FAULTS_DATA):
            r = idx // 2
            c = idx % 2
            btn_text = f"Fault {code} — {name[:24]} ({steps}s)"
            b = tk.Button(grid_frame, text=btn_text, font=("Segoe UI", 9), bg=self.c_border, fg=self.c_text, activebackground=self.c_accent, activeforeground="#11111b", relief="flat", pady=6, anchor="w",
                          command=lambda fcode=code, fname=name, fsteps=steps: self.trigger_specific_fault(fcode, fname, fsteps))
            b.grid(row=r, column=c, padx=4, pady=3, sticky="nsew")
            grid_frame.columnconfigure(c, weight=1)

    def build_tab_highlights(self, parent):
        container = tk.Frame(parent, bg=self.c_bg, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Group 1: Physical Sensor Highlights (FAT, RAT, SAT, Smoke)
        box_sensors = tk.LabelFrame(container, text=" 3D Physical Sensor Highlights (Excel Rows 23–26) ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=10)
        box_sensors.pack(fill=tk.X, pady=(0, 10))

        s_grid = tk.Frame(box_sensors, bg=self.c_card)
        s_grid.pack(fill=tk.X, pady=4)

        self.create_toggle_check(s_grid, "FAT_Sensor_Highlights\n(Fresh Air Temp)", self.var_fat_sensor, self.send_sensor_highlights, 0, 0)
        self.create_toggle_check(s_grid, "RAT_Sensor_Highlights\n(Return Air Temp)", self.var_rat_sensor, self.send_sensor_highlights, 0, 1)
        self.create_toggle_check(s_grid, "SAT_Sensor_Highlights\n(Supply Air Temp)", self.var_sat_sensor, self.send_sensor_highlights, 0, 2)
        self.create_toggle_check(s_grid, "Smoke_Detector_Highlights\n(Smoke Detector Unit)", self.var_smoke_sensor, self.send_sensor_highlights, 0, 3)

        btn_row_s = tk.Frame(box_sensors, bg=self.c_card)
        btn_row_s.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row_s, text="All Sensors ON", bg=self.c_border, fg=self.c_green, relief="flat", padx=10, pady=4, command=lambda: self.set_all_sensors(True)).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row_s, text="All Sensors OFF", bg=self.c_border, fg=self.c_red, relief="flat", padx=10, pady=4, command=lambda: self.set_all_sensors(False)).pack(side=tk.LEFT, padx=4)

        # Group 2: Compressor Highlights (1 to 4)
        box_comps = tk.LabelFrame(container, text=" Compressor Highlights (Excel Rows 19–22) ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=10)
        box_comps.pack(fill=tk.X, pady=(0, 10))

        c_grid = tk.Frame(box_comps, bg=self.c_card)
        c_grid.pack(fill=tk.X, pady=4)

        self.create_toggle_check(c_grid, "Compressor 1\nHighlight", self.var_comp1, self.send_compressor_highlights, 0, 0)
        self.create_toggle_check(c_grid, "Compressor 2\nHighlight", self.var_comp2, self.send_compressor_highlights, 0, 1)
        self.create_toggle_check(c_grid, "Compressor 3\nHighlight", self.var_comp3, self.send_compressor_highlights, 0, 2)
        self.create_toggle_check(c_grid, "Compressor 4\nHighlight", self.var_comp4, self.send_compressor_highlights, 0, 3)

        btn_row_c = tk.Frame(box_comps, bg=self.c_card)
        btn_row_c.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row_c, text="All Compressors ON", bg=self.c_border, fg=self.c_green, relief="flat", padx=10, pady=4, command=lambda: self.set_all_compressors(True)).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row_c, text="All Compressors OFF", bg=self.c_border, fg=self.c_red, relief="flat", padx=10, pady=4, command=lambda: self.set_all_compressors(False)).pack(side=tk.LEFT, padx=4)

        # Group 3: Overall Visualization
        box_vis = tk.LabelFrame(container, text=" Global Visualizations & Maintenance Panels ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=10)
        box_vis.pack(fill=tk.X)

        v_grid = tk.Frame(box_vis, bg=self.c_card)
        v_grid.pack(fill=tk.X, pady=4)
        self.create_toggle_check(v_grid, "Show / Hide Maintenance Panels\n(ShowHideObjects)", self.var_show_hide, self.send_show_hide, 0, 0)
        self.create_toggle_check(v_grid, "Air Flow Arrows Active\n(Arrows)", self.var_arrows, self.send_arrows, 0, 1)
        self.create_toggle_check(v_grid, "Master Compression Highlights\n(Compression_Highlights)", self.var_comp_master, self.send_comp_master, 0, 2)

    def create_toggle_check(self, parent, text, var, cmd, r, c):
        cb = tk.Checkbutton(parent, text=text, variable=var, command=cmd, bg=self.c_card, fg=self.c_text, selectcolor=self.c_border, activebackground=self.c_card, font=("Segoe UI", 9))
        cb.grid(row=r, column=c, padx=8, pady=4, sticky="w")
        parent.columnconfigure(c, weight=1)

    def build_tab_sliders(self, parent):
        container = tk.Frame(parent, bg=self.c_bg, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Top section: Dampers
        box_damp = tk.LabelFrame(container, text=" Damper Blade Positions (BlendShapes 0% to 100%) ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=8)
        box_damp.pack(fill=tk.X, pady=(0, 10))

        for key, label in DAMPER_PARAMS:
            row = tk.Frame(box_damp, bg=self.c_card)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{key} — {label}", width=32, anchor="w", font=("Segoe UI", 9), bg=self.c_card, fg=self.c_text).pack(side=tk.LEFT)
            s = ttk.Scale(row, from_=0, to=10, variable=self.damper_vars[key], orient=tk.HORIZONTAL, command=lambda v: self.send_sliders_payload())
            s.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            val_lbl = tk.Label(row, width=6, font=("Consolas", 9), bg=self.c_card, fg=self.c_accent)
            val_lbl.pack(side=tk.RIGHT)
            self.damper_vars[key].trace_add("write", lambda *_, var=self.damper_vars[key], lbl=val_lbl: lbl.config(text=f"{var.get()*10:.0f}%"))

        # Middle section: Airflow Speeds
        box_speed = tk.LabelFrame(container, text=" Arrow Airflow Speeds (0 to 10) ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=8)
        box_speed.pack(fill=tk.X, pady=(0, 10))

        for key, label in SPEED_PARAMS:
            row = tk.Frame(box_speed, bg=self.c_card)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{key} ({label})", width=32, anchor="w", font=("Segoe UI", 9), bg=self.c_card, fg=self.c_text).pack(side=tk.LEFT)
            s = ttk.Scale(row, from_=0, to=10, variable=self.speed_vars[key], orient=tk.HORIZONTAL, command=lambda v: self.send_sliders_payload())
            s.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            val_lbl = tk.Label(row, width=6, font=("Consolas", 9), bg=self.c_card, fg=self.c_green)
            val_lbl.pack(side=tk.RIGHT)
            self.speed_vars[key].trace_add("write", lambda *_, var=self.speed_vars[key], lbl=val_lbl: lbl.config(text=f"{var.get():.1f}"))

        # Sync button
        tk.Button(container, text="📡 Push Full Telemetry / Slider Stream to Unity", bg=self.c_accent, fg="#11111b", font=("Segoe UI", 10, "bold"), relief="flat", pady=6, command=self.send_sliders_payload).pack(fill=tk.X, pady=6)

    def build_tab_system(self, parent):
        container = tk.Frame(parent, bg=self.c_bg, padx=14, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        box_build = tk.LabelFrame(container, text=" Executable & Simulator Controls ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=12)
        box_build.pack(fill=tk.X, pady=(0, 10))

        tk.Label(box_build, text=f"Target Standalone Executable:\n{BUILD_EXE}", font=("Consolas", 9), bg=self.c_card, fg=self.c_subtext, justify="left").pack(anchor="w", pady=(0, 10))

        row_b = tk.Frame(box_build, bg=self.c_card)
        row_b.pack(fill=tk.X)

        btn_launch = tk.Button(row_b, text="▶ Launch HVAC_V6 Standalone Build", font=("Segoe UI", 10, "bold"), bg="#2e7d32", fg="white", relief="flat", padx=14, pady=8, command=self.launch_build)
        btn_launch.pack(side=tk.LEFT, padx=4)

        btn_quit = tk.Button(row_b, text="🛑 Remote Application Quit (DS3D_OFF)", font=("Segoe UI", 10, "bold"), bg="#c62828", fg="white", relief="flat", padx=14, pady=8, command=self.cmd_quit_app)
        btn_quit.pack(side=tk.LEFT, padx=4)

        box_spec = tk.LabelFrame(container, text=" Alignment & Interface Specification ", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_card, padx=12, pady=12)
        box_spec.pack(fill=tk.BOTH, expand=True)

        spec_text = (
            "• UDP RX Port (Listen from Unity): 5005\n"
            "• UDP TX Port (Send to Unity): 9000\n"
            "• Final Master Workbook: J886_Software_HVAC_phase1-V1_updated_19-Oct 3pm.xlsx (Sheet: DATA TRANSFER)\n"
            "• 4 Sensor Highlights: Rows 23-26 (FAT_Sensor_Highlights, RAT_Sensor_Highlights, SAT_Sensor_Highlights, Smoke_Detector_Highlights)\n"
            "• Fast-Forward Shortcut: Tap 'N' or Right-Arrow inside Unity to immediately step through\n"
            "• Telemetry Events: fault_started, step_completed, sensor_highlight_changed, fault_completed, fault_reset"
        )
        tk.Label(box_spec, text=spec_text, font=("Segoe UI", 9), bg=self.c_card, fg=self.c_text, justify="left").pack(anchor="w")

    def build_telemetry_terminal(self, parent):
        term_frame = tk.Frame(parent, bg=self.c_bg, padx=4, pady=0)
        term_frame.pack(fill=tk.BOTH, expand=True)

        header_row = tk.Frame(term_frame, bg=self.c_bg)
        header_row.pack(fill=tk.X, pady=(0, 6))

        tk.Label(header_row, text="Live UDP Telemetry Monitor (Port 5005)", font=("Segoe UI", 10, "bold"), fg=self.c_accent, bg=self.c_bg).pack(side=tk.LEFT)
        tk.Button(header_row, text="Clear Log", font=("Segoe UI", 8), bg=self.c_border, fg=self.c_text, relief="flat", padx=8, pady=2, command=self.clear_log).pack(side=tk.RIGHT)

        self.txt_log = scrolledtext.ScrolledText(term_frame, bg="#11111b", fg="#cdd6f4", font=("Consolas", 9), insertbackground="white", bd=0)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Tag configurations for colors
        self.txt_log.tag_config("timestamp", foreground="#6c7086")
        self.txt_log.tag_config("sent", foreground="#89b4fa")
        self.txt_log.tag_config("started", foreground="#f9e2af")
        self.txt_log.tag_config("step", foreground="#89dceb")
        self.txt_log.tag_config("completed", foreground="#a6e3a1", font=("Consolas", 9, "bold"))
        self.txt_log.tag_config("reset", foreground="#f38ba8")
        self.txt_log.tag_config("highlight", foreground="#cba6f7")

    # --- NETWORK OPERATIONS ---

    def start_network(self):
        try:
            self.sock_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_rx.bind(("0.0.0.0", LABVIEW_LISTEN_PORT))
            self.sock_rx.settimeout(0.5)

            self.rx_thread = threading.Thread(target=self.rx_loop, daemon=True)
            self.rx_thread.start()
            self.log("SYSTEM", f"Listening on UDP port {LABVIEW_LISTEN_PORT} (Simulating LabVIEW RX)")
        except Exception as ex:
            self.log("ERROR", f"Failed to bind port {LABVIEW_LISTEN_PORT}: {ex}")
            self.lbl_net_status.config(text="● BIND ERROR", fg=self.c_red)

    def rx_loop(self):
        while self.is_running:
            try:
                data, addr = self.sock_rx.recvfrom(4096)
                msg = data.decode("utf-8", errors="replace").strip()
                self.rx_count += 1
                self.after(0, self.handle_incoming_packet, msg)
            except socket.timeout:
                continue
            except Exception:
                break

    def send_udp(self, payload):
        try:
            if isinstance(payload, dict):
                raw = json.dumps(payload).encode("utf-8")
                disp = json.dumps(payload)
            else:
                raw = str(payload).encode("utf-8")
                disp = str(payload)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(raw, (UNITY_IP, UNITY_RX_PORT))
            sock.close()
            self.tx_count += 1
            self.update_tx_rx_labels()
            self.log("SENT", f">>> SENT: {disp}")
        except Exception as ex:
            self.log("ERROR", f"Send failed: {ex}")

    def handle_incoming_packet(self, msg):
        self.update_tx_rx_labels()

        # Try JSON parse
        try:
            parsed = json.loads(msg)
            event = parsed.get("event", "")

            if event == "fault_started":
                self.active_fault_code = parsed.get("fault_code", 0)
                self.total_steps = parsed.get("total_steps", 0)
                self.current_step = 0
                self.total_mistakes = 0
                self.is_completed = False
                self.update_status_display()
                self.log("STARTED", f"<<< [FAULT STARTED] Code: {self.active_fault_code} | Total Steps: {self.total_steps}")
                return

            elif event == "step_completed":
                self.current_step = parsed.get("step_number", self.current_step + 1)
                self.total_mistakes = parsed.get("wrong_attempts", self.total_mistakes)
                self.update_status_display()
                self.log("STEP", f"<<< [STEP COMPLETED] Step {self.current_step}/{self.total_steps} (Mistakes: {self.total_mistakes})")
                return

            elif event == "fault_completed":
                self.is_completed = True
                self.total_mistakes = parsed.get("total_mistakes", self.total_mistakes)
                self.update_status_display()
                self.log("COMPLETED", f"<<< [FAULT COMPLETED] Code: {parsed.get('fault_code')} | Success! Total Mistakes: {self.total_mistakes}")
                return

            elif event == "fault_reset":
                self.active_fault_code = 0
                self.current_step = 0
                self.total_steps = 0
                self.is_completed = False
                self.update_status_display()
                self.log("RESET", "<<< [FAULT RESET] Simulation state returned to IDLE")
                return

            elif event == "sensor_highlight_changed":
                self.log("HIGHLIGHT", f"<<< [SENSOR] '{parsed.get('sensor')}' Highlight -> {parsed.get('status')}")
                return

            elif event == "compression_highlights_changed":
                self.log("HIGHLIGHT", f"<<< [COMPRESSION] Highlights -> {parsed.get('status')}")
                return

            elif event == "arrows_changed":
                self.log("HIGHLIGHT", f"<<< [ARROWS] Flow -> {parsed.get('status')}")
                return

        except Exception:
            pass

        # Raw fallback
        self.log("RECV", f"<<< RECV: {msg}")

    def update_status_display(self):
        if self.active_fault_code > 0:
            self.lbl_active_fault.config(text=f"Fault {self.active_fault_code}", fg=self.c_accent)
            self.lbl_step_counter.config(text=f"{self.current_step} / {self.total_steps}")
        else:
            self.lbl_active_fault.config(text="IDLE", fg=self.c_text)
            self.lbl_step_counter.config(text="0 / 0")

        self.lbl_mistakes.config(text=str(self.total_mistakes))
        if self.is_completed:
            self.lbl_completed.config(text="COMPLETED ✓", fg=self.c_green)
        elif self.active_fault_code > 0:
            self.lbl_completed.config(text="IN PROGRESS", fg=self.c_yellow)
        else:
            self.lbl_completed.config(text="NOT STARTED", fg=self.c_subtext)

    def update_tx_rx_labels(self):
        self.lbl_tx_rx.config(text=f"TX: {self.tx_count} | RX: {self.rx_count}")

    def log(self, category, text):
        ts = time.strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{ts}] ", "timestamp")

        tag = "text"
        if category == "SENT": tag = "sent"
        elif category == "STARTED": tag = "started"
        elif category == "STEP": tag = "step"
        elif category == "COMPLETED": tag = "completed"
        elif category == "RESET": tag = "reset"
        elif category == "HIGHLIGHT": tag = "highlight"

        self.txt_log.insert(tk.END, f"{text}\n\n", tag)
        self.txt_log.see(tk.END)

    def clear_log(self):
        self.txt_log.delete("1.0", tk.END)

    # --- COMMANDS ---

    def cmd_trigger_fault(self):
        sel = self.selected_fault.get()
        code = int(sel.split(":")[0])
        cause = self.selected_cause.get()
        payload = {
            "Hvac": {
                "Fault": [
                    {"Name": "Fault_Code_Trigger", "Value": code},
                    {"Name": "Fault_Cause_Trigger", "Value": cause},
                    {"Name": "Fault_Command_Action", "Value": 1}
                ]
            }
        }
        self.send_udp(payload)

    def trigger_specific_fault(self, code, name, steps):
        self.selected_fault.set(f"{code}: {name} ({steps} steps)")
        self.cmd_trigger_fault()

    def cmd_skip_step(self):
        self.send_udp("skip")

    def cmd_reset_fault(self):
        payload = {
            "Hvac": {
                "Fault": [
                    {"Name": "Fault_Code_Trigger", "Value": 0},
                    {"Name": "Fault_Cause_Trigger", "Value": 0},
                    {"Name": "Fault_Command_Action", "Value": 2}
                ]
            }
        }
        self.send_udp(payload)

    def send_sensor_highlights(self):
        payload = {
            "Hvac": {
                "Boolean": [
                    {"Name": "FAT_Sensor_Highlights", "Value": self.var_fat_sensor.get()},
                    {"Name": "RAT_Sensor_Highlights", "Value": self.var_rat_sensor.get()},
                    {"Name": "SAT_Sensor_Highlights", "Value": self.var_sat_sensor.get()},
                    {"Name": "Smoke_Detector_Highlights", "Value": self.var_smoke_sensor.get()}
                ]
            }
        }
        self.send_udp(payload)

    def set_all_sensors(self, state):
        self.var_fat_sensor.set(state)
        self.var_rat_sensor.set(state)
        self.var_sat_sensor.set(state)
        self.var_smoke_sensor.set(state)
        self.send_sensor_highlights()

    def send_compressor_highlights(self):
        payload = {
            "Hvac": {
                "Boolean": [
                    {"Name": "Compresor 1_Highlights", "Value": self.var_comp1.get()},
                    {"Name": "Compresor 2_Highlights", "Value": self.var_comp2.get()},
                    {"Name": "Compresor 3_Highlights", "Value": self.var_comp3.get()},
                    {"Name": "Compresor 4_Highlights", "Value": self.var_comp4.get()}
                ]
            }
        }
        self.send_udp(payload)

    def set_all_compressors(self, state):
        self.var_comp1.set(state)
        self.var_comp2.set(state)
        self.var_comp3.set(state)
        self.var_comp4.set(state)
        self.send_compressor_highlights()

    def send_show_hide(self):
        payload = {
            "Hvac": {
                "Boolean": [{"Name": "ShowHideObjects", "Value": self.var_show_hide.get()}]
            }
        }
        self.send_udp(payload)

    def send_arrows(self):
        payload = {
            "Hvac": {
                "Boolean": [{"Name": "Arrows", "Value": self.var_arrows.get()}]
            }
        }
        self.send_udp(payload)

    def send_comp_master(self):
        payload = {
            "Hvac": {
                "Boolean": [{"Name": "Compression_Highlights", "Value": self.var_comp_master.get()}]
            }
        }
        self.send_udp(payload)

    def send_sliders_payload(self):
        payload = {
            "Hvac": {
                "Speed": [{"Name": k, "Value": float(self.speed_vars[k].get())} for k, _ in SPEED_PARAMS],
                "Amplitude": (
                    [{"Name": k, "Value": float(self.color_vars[k].get())} for k, _ in COLOR_PARAMS] +
                    [{"Name": k, "Value": float(self.damper_vars[k].get() * 10)} for k, _ in DAMPER_PARAMS]
                )
            }
        }
        self.send_udp(payload)

    def cmd_quit_app(self):
        if messagebox.askyesno("Confirm Shutdown", "Send remote DS3D_OFF shutdown signal to Unity simulator?"):
            payload = {
                "Hvac": {
                    "Boolean": [{"Name": "DS3D_OFF", "Value": 1}]
                }
            }
            self.send_udp(payload)

    def launch_build(self):
        if not os.path.exists(BUILD_EXE):
            messagebox.showerror("Build Not Found", f"Cannot find build at:\n{BUILD_EXE}")
            return
        subprocess.Popen([BUILD_EXE], cwd=os.path.dirname(BUILD_EXE))
        self.log("SYSTEM", f"Launched standalone build: {BUILD_EXE}")

    def destroy(self):
        self.is_running = False
        try:
            if self.sock_rx:
                self.sock_rx.close()
        except Exception:
            pass
        super().destroy()


if __name__ == "__main__":
    app = HVACControlPanel()
    app.mainloop()
