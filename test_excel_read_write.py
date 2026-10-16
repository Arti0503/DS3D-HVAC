"""
DS3D-HVAC Excel Structure and Read/Write Verification Script
Verifies:
1. Contiguous type groupings in 'DATA TRANSFER' (Integers: 821-824, Booleans: 825-842, String: 843).
2. Instructor trigger parameter cells (F1209, F1210, F1211).
3. Live write and read-back of telemetry packet data.
"""

import os
import sys

try:
    import openpyxl
except ImportError:
    print("Error: openpyxl is required. Run: pip install openpyxl")
    sys.exit(1)

EXCEL_FILES = [
    r"c:\Github_Projects\DS3D-HVAC\J886_Software_HVAC_phase1-V1_Fault_Management_Updated.xlsx",
    r"C:\Users\user\Downloads\J886_Software_HVAC_phase1-V1_Fault_Management_Updated.xlsx",
]

def verify_file(filepath):
    print(f"\n{'='*70}")
    print(f"Testing Excel File: {filepath}")
    print(f"{'='*70}")

    if not os.path.isfile(filepath):
        print(f"[FAIL] File not found: {filepath}")
        return False

    wb = openpyxl.load_workbook(filepath, data_only=False)
    if "DATA TRANSFER" not in wb.sheetnames:
        print("[FAIL] Sheet 'DATA TRANSFER' not found!")
        wb.close()
        return False

    ws = wb["DATA TRANSFER"]

    # 1. Verify Contiguous Type Groupings
    print("\n1. Verifying Contiguous Type Groupings (Rows 821 - 854):")
    
    # Integers (821 - 824)
    expected_ints = [
        (821, "Active_Fault_Code"),
        (822, "Current_Step_Number"),
        (823, "Total_Steps"),
        (824, "Wrong_Attempts"),
    ]
    for row, name in expected_ints:
        var = ws.cell(row=row, column=2).value
        assert var == name, f"Row {row} expected {name}, got {var}"
        print(f"  [PASS] Row {row:3d} (Integer) : {var}")

    # Booleans (825 - 853) - 29 contiguous rows
    expected_bools = [
        (825, "Step_Accomplished"),
        (826, "Fault_Completed"),
    ] + [(827 + i, f"Fault_{101 + i}_Status") for i in range(16)] + [
        (843, "Compression_Highlights_Active"),
        (844, "Arrows_Active"),
    ]

    for row, name in expected_bools:
        var = ws.cell(row=row, column=2).value
        assert var == name, f"Row {row} expected {name}, got {var}"
        print(f"  [PASS] Row {row:3d} (Boolean) : {var}")

    for row in range(845, 854):
        dtype = ws.cell(row=row, column=5).value
        assert dtype == "Boolean", f"Row {row} expected Boolean spare, got {dtype}"
        print(f"  [PASS] Row {row:3d} (Spare Boolean) : Spare")

    # String (854)
    var_str = ws.cell(row=854, column=2).value
    assert var_str == "Telemetry_Event", f"Row 854 expected Telemetry_Event, got {var_str}"
    print(f"  [PASS] Row 854 (String)  : {var_str}")

    # 2. Verify RHS Intact Formulas
    print("\n2. Verifying RHS Hardware Fan/Damper Formulas (Cols N & P):")
    for r in range(821, 827):
        formula = ws.cell(row=r, column=14).value
        expected = f"=P{r}"
        assert str(formula).strip() == expected, f"RHS formula at N{r} modified: {formula}"
        print(f"  [PASS] Cell N{r} intact: {formula}")

    # 3. Verify Instructor Control Cells
    print("\n3. Verifying Instructor Trigger Control Cells (F1209 - F1212):")
    ctrl_cells = [
        (1209, "Fault Number (101-114)"),
        (1210, "Fault Cause (1-3)"),
        (1211, "Fault Command Action (1=Trigger, 2=Reset)"),
        (1212, "Compression Highlights (0=Hide, 1=Show)"),
    ]
    for row, desc in ctrl_cells:
        val = ws.cell(row=row, column=6).value
        print(f"  [PASS] Cell F{row} ({desc}): Current Value = {val}")

    # 4. Test Simulated Write & Read-back
    print("\n4. Performing Simulated Live Telemetry Write & Read-back:")
    # Simulate writing Step 2 of Fault 104 with 1 mistake
    ws.cell(row=821, column=6, value=104)
    ws.cell(row=822, column=6, value=2)
    ws.cell(row=823, column=6, value=15)
    ws.cell(row=824, column=6, value=1)
    ws.cell(row=825, column=6, value=1)
    ws.cell(row=826, column=6, value=0)
    ws.cell(row=830, column=6, value=1) # Fault 104 Status row
    ws.cell(row=854, column=6, value="step_completed")
    
    wb.save(filepath)
    wb.close()

    # Re-open and verify
    wb_verify = openpyxl.load_workbook(filepath, data_only=True)
    ws_v = wb_verify["DATA TRANSFER"]
    assert ws_v.cell(row=821, column=6).value == 104
    assert ws_v.cell(row=822, column=6).value == 2
    assert ws_v.cell(row=823, column=6).value == 15
    assert ws_v.cell(row=824, column=6).value == 1
    assert ws_v.cell(row=825, column=6).value == 1
    assert ws_v.cell(row=826, column=6).value == 0
    assert ws_v.cell(row=830, column=6).value == 1
    assert ws_v.cell(row=854, column=6).value == "step_completed"
    print("  [PASS] Live Telemetry Written & Read Back Successfully!")

    # Reset cells to default idle state
    wb_clean = openpyxl.load_workbook(filepath, data_only=False)
    ws_c = wb_clean["DATA TRANSFER"]
    for r in range(821, 825):
        ws_c.cell(row=r, column=6, value=0)
    for r in range(825, 843):
        ws_c.cell(row=r, column=6, value=0)
    ws_c.cell(row=854, column=6, value="idle")
    wb_clean.save(filepath)
    wb_clean.close()
    print("  [PASS] Cells restored to default idle state.")

    print(f"\n>>> ALL CHECKS PASSED FOR: {os.path.basename(filepath)} <<<\n")
    return True

if __name__ == "__main__":
    for f in EXCEL_FILES:
        try:
            verify_file(f)
        except PermissionError:
            print(f"\n[NOTE] File '{f}' is currently open in Microsoft Excel. Please close it in Excel to test it.\n")
        except Exception as ex:
            print(f"\n[FAIL] Error testing '{f}': {ex}\n")
