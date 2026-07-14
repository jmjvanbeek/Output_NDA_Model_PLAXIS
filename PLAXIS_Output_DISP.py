"""
Professional PLAXIS Output Export Script (OPTIMIZED + PAIRED RESIDUALS)
-----------------------------------------------------------------------
- Extracts Ux and Uy for defined top nodes in PLAXIS input and in the script for every motion
- Alters the collected Ux and Uy data with the residual displacement from the bottom nodes for every motion

- Extracts the Ux over depth at chosen crosssections for every motion
- Alters the collected Ux over depth at chosen crosssections with the bottom value for every motion

Output:
CSV files of extracted data

Author: 924878 (JMJB)
Date: 202603
"""

# ============================================================
# MULTI-MOTION SCRIPT — CN Node Pairs + Cross-Sections
# With: subfolders, combined CSVs per motion, runtime timers,
# PLAXIS-native line-cross-section extraction.
# ============================================================

import math
import os
import time
from plxscripting.easy import new_server

PW = "#f#%Rk992sYiAaw1"
INPUT_PORT = 10000

# ------------------------------------------------------------
# USER INPUT
# ------------------------------------------------------------
MOTION_LIST = [
    "Motion_4869",
    #"Motion_4032463",
    #"Motion_6001145",
    #"Motion_188",
    #"Motion_78",
    #"Motion_78",
]

# Node pairs to process
NODE_PAIRS = [
    ("CN_1", "CN_3"),
    ("CN_2", "CN_3"),
]

# Cross-sections (Ux only)
CROSS_SECTIONS = [
    ("Crest", 127.8, 6.04, -92.00),
    ("Toe", 211.3, -12.76,  -92.00),
]

OUT_DIR = r"C:\Users\924878\OneDrive - Haskoning\PycharmProjects\PLAXIS\Result_Displacement"

# Subdirectories for output
CS_DIR   = os.path.join(OUT_DIR, "Cross_sections")
NODE_DIR = os.path.join(OUT_DIR, "Node_displacements")
os.makedirs(CS_DIR, exist_ok=True)
os.makedirs(NODE_DIR, exist_ok=True)

# Feature switches
RUN_NODE_PAIR_DISPLACEMENTS = True
RUN_CROSS_SECTIONS          = True

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def find_input_phase(g_i, motion_name: str):
    tgt = motion_name.strip().lower()
    for p in g_i.Phases:
        if str(p.Identification).strip().lower() == tgt:
            return p
    return None

def map_input_to_output_phase(g_i, input_phase):
    port = g_i.view(input_phase)
    time.sleep(0.5)
    s_o, g_o = new_server("localhost", port, password=PW)

    internal = str(input_phase.Name)

    # Try internal name
    for op in g_o.Phases:
        try:
            if str(op.Name.value) == internal:
                return s_o, g_o, op
        except:
            pass

    # Try identification fallback
    tgt = str(input_phase.Identification).strip().lower()
    for op in g_o.Phases:
        try:
            if str(op.Identification).strip().lower() == tgt:
                return s_o, g_o, op
        except:
            pass

    raise RuntimeError(f"Could not map Input→Output phase for {input_phase.Identification}")

def get_step_time_safe(step):
    try:
        if hasattr(step, "Reached") and hasattr(step.Reached, "Time"):
            return float(step.Reached.Time.value)
    except:
        pass
    return None

# ------------------------------------------------------------
# PROCESS NODE DISPLACEMENTS (CN pairs)
# ------------------------------------------------------------
def process_motion_node_pairs(g_i, motion_name):
    print(f"\n=== START NODE-PAIRS for MOTION: {motion_name} ===")

    ph_in = find_input_phase(g_i, motion_name)
    if ph_in is None:
        print(f"[ERR] Motion not found: {motion_name}")
        return None

    s_o, g_o, ph_out = map_input_to_output_phase(g_i, ph_in)
    print(f"[OK] Output phase = {ph_out.Name.value}")

    # Steps
    try:
        steps = list(ph_out.Steps.value)
    except:
        steps = list(ph_out.Steps)

    if not steps:
        print("[ERR] No steps found.")
        return None

    N = len(steps)
    print(f"[OK] Steps: {N}")

    # Build CP map
    cp_map = {}
    for cp in g_o.CurvePoints:
        try:
            nm = cp.Name.value  # "CN_17"
            if nm.startswith("CN_"):
                num = int(nm.split("_")[1])
                cp_map[num] = cp
        except:
            pass

    # Validate
    for cnA, cnB in NODE_PAIRS:
        if int(cnA.split("_")[1]) not in cp_map or int(cnB.split("_")[1]) not in cp_map:
            print(f"[ERR] Missing CP for pair {cnA}-{cnB}")
            return None

    # Data store for combined CSV
    node_data = {}
    time_vec = []

    # Main extraction loop per pair
    for cnA, cnB in NODE_PAIRS:
        print(f"\n--- PROCESSING PAIR {cnA} & {cnB} ---")
        cpA = cp_map[int(cnA.split("_")[1])]
        cpB = cp_map[int(cnB.split("_")[1])]

        uxA = []; uxB = []; uyA = []; uyB = []
        resid_ux = []; resid_uy = []

        print(f"[INFO] Extracting Ux & Uy...")

        for i, st in enumerate(steps, start=1):
            pct = (i / N) * 100
            print(f"\rProgress {motion_name} {cnA}-{cnB}: {pct:5.1f}% ({i}/{N})", end="")

            # Time (store only once)
            t = get_step_time_safe(st)
            if len(time_vec) < N:
                time_vec.append(t)

            # Ux
            try:  vA_x = g_o.getcurveresults(cpA, st, g_o.ResultTypes.Soil.Ux)
            except: vA_x = float("nan")
            try:  vB_x = g_o.getcurveresults(cpB, st, g_o.ResultTypes.Soil.Ux)
            except: vB_x = float("nan")

            # Uy
            try: vA_y = g_o.getcurveresults(cpA, st, g_o.ResultTypes.Soil.Uy)
            except: vA_y = float("nan")
            try: vB_y = g_o.getcurveresults(cpB, st, g_o.ResultTypes.Soil.Uy)
            except: vB_y = float("nan")

            uxA.append(vA_x); uxB.append(vB_x)
            uyA.append(vA_y); uyB.append(vB_y)

            resid_ux.append(vA_x - vB_x if math.isfinite(vA_x) and math.isfinite(vB_x) else float("nan"))
            resid_uy.append(vA_y - vB_y if math.isfinite(vA_y) and math.isfinite(vB_y) else float("nan"))

        print()  # newline

        # Store for combined CSV
        node_data[(cnA, cnB)] = {
            "uxA": uxA, "uxB": uxB, "resid_ux": resid_ux,
            "uyA": uyA, "uyB": uyB, "resid_uy": resid_uy
        }

    # ------------------------------------------------------
    # Combined CSV for all node pairs
    # ------------------------------------------------------
    combined_csv = os.path.join(NODE_DIR, f"{motion_name}_Node_Displacements.csv")

    header = ["Time[s]"]
    for (cnA, cnB) in NODE_PAIRS:
        header += [
            f"Ux({cnA})", f"Ux({cnB})", f"Ux_Residual({cnA}-{cnB})",
            f"Uy({cnA})", f"Uy({cnB})", f"Uy_Residual({cnA}-{cnB})"
        ]

    with open(combined_csv, "w", encoding="cp1252", newline="") as f:
        f.write("SEP=;\n")
        f.write(";".join(header) + "\n")

        for i, t in enumerate(time_vec):
            row = [f"{t:.6f}" if t is not None else ""]
            for pair in NODE_PAIRS:
                d = node_data[pair]
                row.append(f"{d['uxA'][i]:.6f}" if math.isfinite(d['uxA'][i]) else "")
                row.append(f"{d['uxB'][i]:.6f}" if math.isfinite(d['uxB'][i]) else "")
                row.append(f"{d['resid_ux'][i]:.6f}" if math.isfinite(d['resid_ux'][i]) else "")
                row.append(f"{d['uyA'][i]:.6f}" if math.isfinite(d['uyA'][i]) else "")
                row.append(f"{d['uyB'][i]:.6f}" if math.isfinite(d['uyB'][i]) else "")
                row.append(f"{d['resid_uy'][i]:.6f}" if math.isfinite(d['resid_uy'][i]) else "")
            f.write(";".join(row) + "\n")

    print(f"[OK] Combined node displacement CSV saved → {combined_csv}")
    print(f"=== FINISHED NODE-PAIRS for {motion_name} ===")

    return node_data  # in case you want to use later

# ------------------------------------------------------------
# CROSS-SECTIONS (PLAXIS-native)
# ------------------------------------------------------------
def process_cross_sections_for_motion(g_o, out_phase, motion_name):

    cs_data_ux = {}
    cs_data_ux_resid = {}

    cs_data_uy = {}
    cs_data_uy_resid = {}

    for (label, xcs, ytop, ybot) in CROSS_SECTIONS:

        ini_plot = g_o.Plots[-1]
        pt_top = (xcs, ytop)
        pt_bot = (xcs, ybot)

        cs_plot = g_o.linecrosssectionplot(ini_plot, pt_top, pt_bot)

        # ---- extract y-coords ----
        Ys = g_o.getcrosssectionresults(cs_plot, out_phase, g_o.ResultTypes.Soil.Y)
        ys = [float(v) for v in Ys]

        # ---- extract Ux ----
        Uxs = g_o.getcrosssectionresults(cs_plot, out_phase, g_o.ResultTypes.Soil.Ux)
        usx = [float(v) for v in Uxs]

        # ---- extract Uy ----
        Uys = g_o.getcrosssectionresults(cs_plot, out_phase, g_o.ResultTypes.Soil.Uy)
        usy = [float(v) for v in Uys]

        # ---- sort by depth top→bottom ----
        zipped_ux = sorted(zip(ys, usx), key=lambda r: r[0], reverse=True)
        zipped_uy = sorted(zip(ys, usy), key=lambda r: r[0], reverse=True)

        ys_sorted_ux = [y for y,_ in zipped_ux]
        ux_sorted    = [u for _,u in zipped_ux]

        ys_sorted_uy = [y for y,_ in zipped_uy]
        uy_sorted    = [u for _,u in zipped_uy]

        # --- residual bottom correction ---
        bottom_ux = ux_sorted[-1] if math.isfinite(ux_sorted[-1]) else 0.0
        bottom_uy = uy_sorted[-1] if math.isfinite(uy_sorted[-1]) else 0.0

        ux_resid = [(u - bottom_ux) if math.isfinite(u) else float("nan") for u in ux_sorted]
        uy_resid = [(u - bottom_uy) if math.isfinite(u) else float("nan") for u in uy_sorted]

        cs_data_ux[label] = (ys_sorted_ux, ux_sorted)
        cs_data_ux_resid[label] = (ys_sorted_ux, ux_resid)

        cs_data_uy[label] = (ys_sorted_uy, uy_sorted)
        cs_data_uy_resid[label] = (ys_sorted_uy, uy_resid)

        print(f"[OK] Extracted CS '{label}' (Ux & Uy) for motion {motion_name}")

    return cs_data_ux, cs_data_ux_resid, cs_data_uy, cs_data_uy_resid

# ------------------------------------------------------------
# WRITE CS (CSV + PNG)
# ------------------------------------------------------------
def write_cross_section_csvs_single_motion(motion_name, cs_ux, cs_ux_resid, cs_uy, cs_uy_resid):
    """
    Schrijft per cross-section en per motion twee bestanden weg:
    - *_xdisp_profile_{motion}.csv   met kolommen: y;Ux;Ux_RESID
    - *_ydisp_profile_{motion}.csv   met kolommen: y;Uy;Uy_RESID
    """
    # mapping from CS label → bestandsnaam-prefix
    label_map = {
        "Toe": "toe",
        "Crest": "crest",
        "Middle": "midslope",
    }

    for (label, *_rest) in CROSS_SECTIONS:
        prefix = label_map.get(label, label.lower())

        # --------- X displacement (Ux + residual) ----------
        ys_x, ux_vals = cs_ux[label]
        _ys_xr, ux_resid_vals = cs_ux_resid[label]

        # sanity: lengte gelijk trekken (PLAXIS levert gelijke lengte, maar toch defensief)
        n = min(len(ys_x), len(ux_vals), len(ux_resid_vals))
        ys_x = ys_x[:n]
        ux_vals = ux_vals[:n]
        ux_resid_vals = ux_resid_vals[:n]

        x_path = os.path.join(CS_DIR, f"{prefix}_xdisp_profile_{motion_name}.csv")
        with open(x_path, "w", encoding="cp1252", newline="") as f:
            f.write("SEP=;\n")
            f.write("y;Ux;Ux_RESID\n")
            for y, u, ur in zip(ys_x, ux_vals, ux_resid_vals):
                y_str  = f"{y:.6f}"
                ux_str = f"{u:.6f}"  if math.isfinite(u)  else ""
                ur_str = f"{ur:.6f}" if math.isfinite(ur) else ""
                f.write(f"{y_str};{ux_str};{ur_str}\n")

        print(f"[OK] CS Ux (incl. RESID) saved → {x_path}")

        # --------- Y displacement (Uy + residual) ----------
        ys_y, uy_vals = cs_uy[label]
        _ys_yr, uy_resid_vals = cs_uy_resid[label]

        n = min(len(ys_y), len(uy_vals), len(uy_resid_vals))
        ys_y = ys_y[:n]
        uy_vals = uy_vals[:n]
        uy_resid_vals = uy_resid_vals[:n]

        y_path = os.path.join(CS_DIR, f"{prefix}_ydisp_profile_{motion_name}.csv")
        with open(y_path, "w", encoding="cp1252", newline="") as f:
            f.write("SEP=;\n")
            f.write("y;Uy;Uy_RESID\n")
            for y, u, ur in zip(ys_y, uy_vals, uy_resid_vals):
                y_str  = f"{y:.6f}"
                uy_str = f"{u:.6f}"  if math.isfinite(u)  else ""
                ur_str = f"{ur:.6f}" if math.isfinite(ur) else ""
                f.write(f"{y_str};{uy_str};{ur_str}\n")

        print(f"[OK] CS Uy (incl. RESID) saved → {y_path}")

# ------------------------------------------------------------
# PROCESS ONE MOTION
# ------------------------------------------------------------
def process_motion(g_i, motion_name):

    start_t = time.time()

    if RUN_NODE_PAIR_DISPLACEMENTS:
        process_motion_node_pairs(g_i, motion_name)
    else:
        print(f"[SKIP] Node-pair extraction disabled for {motion_name}")

    if RUN_CROSS_SECTIONS:
        ph_in = find_input_phase(g_i, motion_name)
        s_o, g_o, ph_out = map_input_to_output_phase(g_i, ph_in)

        cs_ux, cs_ux_resid, cs_uy, cs_uy_resid = process_cross_sections_for_motion(g_o, ph_out, motion_name)
        write_cross_section_csvs_single_motion(motion_name, cs_ux, cs_ux_resid, cs_uy, cs_uy_resid)

    end_t = time.time()
    print(f"\n[MOTION DONE] {motion_name} completed in {end_t - start_t:.2f} seconds\n")

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():

    print("\n=== MULTI-MOTION EXPORT START ===\n")

    s_i, g_i = new_server("localhost", INPUT_PORT, password=PW)

    for motion in MOTION_LIST:
        process_motion(g_i, motion)


    print("\n=== MULTI-MOTION EXPORT COMPLETE ===\n")

if __name__ == "__main__":
    main()