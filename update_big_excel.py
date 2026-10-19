import openpyxl

def update_big_excel():
    excel_path = r"C:\Github_Projects\DS3D-HVAC\J886_Software_HVAC_phase1-V1_Fault_Management_Updated.xlsx"
    print(f"Loading {excel_path}...")
    wb = openpyxl.load_workbook(excel_path)
    
    ws = wb["DATA TRANSFER"]
    
    # -------------------------------------------------------------------------
    # 1. Edit Left Side (Inputs from DS3D): Rows 843 and 844
    # Replace Compression_Highlights_Active and Arrows_Active with Submit and Attempts Summary
    # -------------------------------------------------------------------------
    
    # Row 843 (SR.No 23): Compression_Highlights_Active -> Fault_Submit_Status
    ws.cell(843, 1).value = 23
    ws.cell(843, 2).value = "Fault_Submit_Status"
    ws.cell(843, 3).value = "Repaired Fault Submit Status"
    ws.cell(843, 4).value = "State"
    ws.cell(843, 5).value = "Boolean"
    ws.cell(843, 6).value = 0
    ws.cell(843, 7).value = "0: In Progress, 1: Submitted via UI Submit Button"
    print("Updated Row 843: Fault_Submit_Status")

    # Row 844 (SR.No 24): Arrows_Active -> Steps_Attempts_Summary
    ws.cell(844, 1).value = 24
    ws.cell(844, 2).value = "Steps_Attempts_Summary"
    ws.cell(844, 3).value = "Step Attempts Summary Payload"
    ws.cell(844, 4).value = "Telemetry"
    ws.cell(844, 5).value = "String"
    ws.cell(844, 6).value = "0"
    ws.cell(844, 7).value = "Byte-serialized or comma-separated attempt history per step"
    print("Updated Row 844: Steps_Attempts_Summary")

    # -------------------------------------------------------------------------
    # 2. Edit Right Side (Outputs to DS3D): Rows 839 and 840
    # Remove extra visual highlight controls (ShowHideObjects, Compression_Highlights)
    # -------------------------------------------------------------------------
    
    # Row 839: ShowHideObjects -> Spare
    ws.cell(839, 9).value = 19
    ws.cell(839, 10).value = "Spare"
    ws.cell(839, 11).value = "Spare"
    ws.cell(839, 12).value = "Spare"
    ws.cell(839, 13).value = "Integer"
    ws.cell(839, 14).value = 0
    ws.cell(839, 15).value = "Spare"
    print("Updated Row 839 (Right): Spare")

    # Row 840: Compression_Highlights -> Spare
    ws.cell(840, 9).value = 20
    ws.cell(840, 10).value = "Spare"
    ws.cell(840, 11).value = "Spare"
    ws.cell(840, 12).value = "Spare"
    ws.cell(840, 13).value = "Integer"
    ws.cell(840, 14).value = 0
    ws.cell(840, 15).value = "Spare (Compression highlights excluded)"
    print("Updated Row 840 (Right): Spare")

    # -------------------------------------------------------------------------
    # 3. Edit Instructor Inputs: Row 1212
    # Clean Compression_Highlights to standard Spare
    # -------------------------------------------------------------------------
    ws.cell(1212, 1).value = 4
    ws.cell(1212, 2).value = "Spare"
    ws.cell(1212, 3).value = "Spare"
    ws.cell(1212, 4).value = "Integer"
    ws.cell(1212, 5).value = "Instructor UI"
    ws.cell(1212, 6).value = 0
    ws.cell(1212, 7).value = "Spare (Compression highlights excluded)"
    print("Updated Row 1212: Spare")

    print(f"Saving {excel_path}...")
    wb.save(excel_path)
    print("Saved successfully without touching any other sheets or formulas!")

if __name__ == "__main__":
    update_big_excel()
