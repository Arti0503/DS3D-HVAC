import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

src_path = r"C:\Github_Projects\DS3D-HVAC\J886_Software_HVAC_phase1-V1_updated_19-Oct 3pm.xlsx"
dst_path = r"C:\Github_Projects\DS3D-HVAC\DS3D_HVAC_Fault_Integration_Handover.xlsx"

src_wb = openpyxl.load_workbook(src_path, data_only=True)
dst_wb = openpyxl.Workbook()
dst_wb.remove(dst_wb.active)

# 1. CREATE DATA TRANSFER TAB STARTING AT ROW 1
ws_dt = dst_wb.create_sheet(title='DATA TRANSFER')
src_dt = src_wb['DATA TRANSFER']

# Copy rows 816 to 869 to rows 1 to 54
row_offset = 816 - 1
for r in range(816, 870):
    target_r = r - row_offset
    for c in range(1, 20):
        val = src_dt.cell(r, c).value
        if val is not None:
            ws_dt.cell(target_r, c, value=val)

# Auto-fit column widths for DATA TRANSFER
for col in ws_dt.columns:
    max_len = max(len(str(cell.value or '')) for cell in col)
    col_letter = get_column_letter(col[0].column)
    ws_dt.column_dimensions[col_letter].width = max(max_len + 3, 10)

# 2. COPY FAULT LOGIC TAB
ws_fl = dst_wb.create_sheet(title='Fault Logic')
src_fl = src_wb['Fault Logic']

for r in range(1, src_fl.max_row + 1):
    for c in range(1, src_fl.max_column + 1):
        val = src_fl.cell(r, c).value
        if val is not None:
            ws_fl.cell(r, c, value=val)

# Auto-fit column widths for Fault Logic
for col in list(ws_fl.columns)[:30]:
    max_len = max(len(str(cell.value or '')) for cell in col[:15])
    col_letter = get_column_letter(col[0].column)
    ws_fl.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

# 3. CREATE NETWORK & UDP PROTOCOL TAB
ws_net = dst_wb.create_sheet(title='UDP Network Protocol')
net_rows = [
    ['DS3D-HVAC Simulation — Network Communication & UDP Integration Guide'],
    ['Target: Unity DS3D Simulator <-> External Controller / Host Software'],
    [],
    ['1. NETWORK ENDPOINT CONFIGURATION'],
    ['Parameter', 'Host Software Side', 'Unity DS3D Side', 'Description'],
    ['Command Port (TX to Unity)', 'Sends to Port 9000', 'Listens on Port 9000', 'UDP Datagrams: Trigger faults, reset, arrow controls, highlights'],
    ['Telemetry Port (RX from Unity)', 'Listens on Port 5005', 'Sends to Port 5005', 'UDP Datagrams: Live step progress, wrong attempts, fault completion'],
    ['Target IP', '127.0.0.1 (Localhost or LAN IP)', '127.0.0.1', 'Unity automatically captures sender IP and routes replies back'],
    ['Payload Encoding', 'UTF-8 String / JSON', 'UTF-8 String / JSON', 'Standard JSON strings or raw integer codes'],
    [],
    ['2. INBOUND COMMAND PAYLOADS (Host -> Unity Port 9000)'],
    ['Action', 'JSON Payload Example', 'Raw String Fallback', 'Unity Response on Port 5005'],
    ['Trigger Fault Scenario', '{"command": "trigger_fault", "fault_code": 104}', '104', 'Returns: {"event": "fault_started", "fault_code": 104, "total_steps": 15, ...}'],
    ['Reset to Normal / Idle', '{"command": "reset"}', 'reset', 'Returns: {"event": "compression_highlights_changed", "compression_highlights": true, ...}'],
    ['Skip Current Step', '{"command": "skip_step"}', 'skip', 'Advances procedure by 1 step in Unity'],
    ['Airflow Arrow Speeds (0-10)', '{"Hvac": {"Speed": [{"Name": "BlueArrowOut", "Value": 5.0}, {"Name": "Fan1", "Value": 5.0}]}}', 'N/A', 'Echoes comma-separated float array'],
    ['Highlight Toggles', '{"Hvac": {"Boolean": [{"Name": "FAT_Sensor_Highlights", "Value": true}]}}', 'N/A', 'Returns: {"event": "sensor_highlight_changed", "sensor": "FAT", "is_visible": true}'],
    ['Casing Visibility Toggle', '{"Hvac": {"Boolean": [{"Name": "ShowHideObjects", "Value": true}]}}', 'N/A', 'Toggles outer casing cutaway visibility'],
    [],
    ['3. OUTBOUND TELEMETRY (Unity Port 5005 -> Host)'],
    ['Event Type', 'JSON Schema Example', 'Trigger Condition', 'Usage in Host / LabVIEW'],
    ['fault_started', '{"event": "fault_started", "fault_code": 104, "total_steps": 15, "status": "started"}', 'Sent immediately when fault is activated', 'Initialize student exam timer & total step indicator'],
    ['step_completed', '{"event": "step_completed", "fault_code": 104, "step_number": 1, "wrong_attempts": 0, "total_steps": 15, "status": "success"}', 'Sent upon each successful tool/part interaction', 'Update Current_Step_Number and Wrong_Attempts scoring'],
    ['fault_completed', '{"event": "fault_completed", "fault_code": 104, "total_steps": 15, "total_mistakes": 0, "status": "success"}', 'Sent after final step is completed', 'Display final exam grade / completion banner']
]

for r_idx, row in enumerate(net_rows, 1):
    for c_idx, val in enumerate(row, 1):
        ws_net.cell(r_idx, c_idx, value=val)

for col in ws_net.columns:
    max_len = max(len(str(cell.value or '')) for cell in col[:25])
    col_letter = get_column_letter(col[0].column)
    ws_net.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 50)

# Also create a pure single-tab version if they strictly want only the DATA TRANSFER tab!
ws_single = dst_wb.copy_worksheet(ws_dt)
ws_single.title = "DATA_TRANSFER_ONLY"

dst_wb.save(dst_path)

# Save also a strictly single-sheet workbook:
dst_single_path = r"C:\Github_Projects\DS3D-HVAC\DS3D_HVAC_DATA_TRANSFER_Only.xlsx"
wb_single = openpyxl.Workbook()
ws_s = wb_single.active
ws_s.title = "DATA TRANSFER"
for r in range(1, ws_dt.max_row + 1):
    for c in range(1, ws_dt.max_column + 1):
        ws_s.cell(r, c, value=ws_dt.cell(r, c).value)
for col in ws_s.columns:
    max_len = max(len(str(cell.value or '')) for cell in col)
    col_letter = get_column_letter(col[0].column)
    ws_s.column_dimensions[col_letter].width = max(max_len + 3, 10)

wb_single.save(dst_single_path)

print(f"Generated clean handover workbook: {dst_path}")
print(f"Generated single-tab workbook:      {dst_single_path}")
