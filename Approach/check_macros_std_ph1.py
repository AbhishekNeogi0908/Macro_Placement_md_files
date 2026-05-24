import json
import os
import sys
from collections import Counter

# ==========================================
# Path Configuration
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "adaptec1"))
RESULTS_DIR = os.path.join(DATA_DIR, "Results")

JSON_IN = os.path.join(RESULTS_DIR, "clustered_macros.json")
NODES_FILE = os.path.join(DATA_DIR, "adaptec1.nodes")
PL_FILE = os.path.join(DATA_DIR, "adaptec1.pl")

def verify_paths():
    """Ensure all required pipeline files exist before running verification."""
    missing = [f for f in [JSON_IN, NODES_FILE, PL_FILE] if not os.path.exists(f)]
    if missing:
        print("❌ ERROR: Missing required database files for verification:")
        for m in missing:
            print(f"   - {m}")
        sys.exit(1)

def analyze_standard_cell_properties():
    """Parses .nodes to dynamically locate the uniform row height of standard cells."""
    all_heights = []
    node_dimensions = {}
    
    with open(NODES_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('UCLA', '#', 'NumNodes', 'NumTerminals')):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    name, w, h = parts[0], int(parts[1]), int(parts[2])
                    node_dimensions[name] = (w, h)
                    all_heights.append(h)
                except ValueError:
                    continue
                    
    # The most frequent height is the standard cell placement row height (usually 12)
    std_row_height = Counter(all_heights).most_common(1)[0][0] if all_heights else 12
    return node_dimensions, std_row_height

def check_cluster_purity():
    verify_paths()
    
    # 1. Load the dynamic layout geometry references
    node_dimensions, std_row_height = analyze_standard_cell_properties()
    
    # 2. Load the current Phase 1 output cluster dictionary
    with open(JSON_IN, 'r') as f:
        clusters = json.load(f)

    print("=" * 80)
    print("         CRITICAL PIPELINE CHECK: CLUSTER PURITY AUDIT REPORT        ")
    print("=" * 80)
    print(f"ℹ️  Baseline Standard Cell Row Height: {std_row_height} units")
    print(f"ℹ️  Filtering Logic Threshold: Area <= 9999 OR Height == {std_row_height}\n")

    total_standard_cells_found = 0
    total_macros_found = 0
    corrupted_clusters = 0

    for c_id in sorted(clusters.keys(), key=int):
        macros_dict = clusters[c_id]
        
        cluster_macros = []
        cluster_standard_cells = []
        
        for node_name in macros_dict.keys():
            # Get dimensions from the source of truth (.nodes file)
            w, h = node_dimensions.get(node_name, (0, 0))
            area = w * h
            
            # --- EXACT FILTERING GATING LOGIC ---
            if area <= 9999 or h == std_row_height:
                cluster_standard_cells.append((node_name, w, h, area))
            else:
                cluster_macros.append((node_name, w, h, area))
                
        num_cells = len(cluster_standard_cells)
        num_macros = len(cluster_macros)
        total_standard_cells_found += num_cells
        total_macros_found += num_macros
        
        if num_cells > 0:
            corrupted_clusters += 1
            print(f"🚨 Cluster {c_id:<3} -> CORRUPTED! Contains: {num_macros:<3} True Macros | {num_cells:<3} Standard Cells")
            print("    🔴 Stray Standard Cells Identified:")
            cell_details = [f"{name}({w}x{h}, area:{a})" for name, w, h, a in cluster_standard_cells]
            # Wrap items into clean terminal lists
            chunks = [cell_details[x:x+4] for x in range(0, len(cell_details), 4)]
            for chunk in chunks:
                print("      " + ", ".join(chunk))
            print("-" * 80)
        else:
            print(f"✅ Cluster {c_id:<3} -> PURE MACRO ENVIRONMENT. Contains: {num_macros:<3} True Macros | 0 Standard Cells")

    print("=" * 80)
    print("📊 FINAL AUDIT ANALYSIS MATRIX SUMMARY:")
    print("-" * 80)
    print(f"🚀 Total Valid Movable Macros Safely Grouped:   {total_macros_found}")
    print(f"🔒 Total Stray Standard Cells Leaked:           {total_standard_cells_found}")
    print(f"📁 Total Number of Corrupted Mixed Clusters:    {corrupted_clusters}")
    print("=" * 80)
    
    if total_standard_cells_found == 0:
        print("🎉 SUCCESS! Your current clustered_macros.json file is 100% PURE.")
        print("💡 You are completely clear to run Phase 3 (Anchors) and Phase 4 (Gurobi).")
    else:
        print("⚠️  WARNING: Standard cells are still present. Please clean your partition input loops.")
    print("=" * 80)

if __name__ == "__main__":
    check_cluster_purity()