import json
import os
from collections import Counter

# Configuration Paths - Update to match your actual folders
DATA_DIR = "/home/abhishek-u-24-rs2/Macro_Placement/adaptec1"
RESULTS_DIR = os.path.join(DATA_DIR, "Results")

CLUSTERS_FILE = os.path.join(RESULTS_DIR, "clustered_macros.json")
NODES_FILE = os.path.join(DATA_DIR, "adaptec1.nodes")

def analyze_design_components(nodes_file):
    """
    Parses the .nodes file to profile components.
    Standard cells will dominate the file and share a single uniform row height.
    """
    if not os.path.exists(nodes_file):
        print(f"❌ ERROR: Nodes file missing at {nodes_file}")
        return {}, None

    node_dimensions = {}
    all_heights = []
    
    print("📐 Scanning .nodes database to extract physical component profiles...")
    with open(nodes_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('UCLA', '#', 'NumNodes', 'NumTerminals')):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    node_name = parts[0]
                    w = int(parts[1])
                    h = int(parts[2])
                    node_dimensions[node_name] = (w, h)
                    all_heights.append(h)
                except ValueError:
                    continue

    if not all_heights:
        return {}, None

    # Dynamically find the standard cell row height (the most common height value)
    std_row_height = Counter(all_heights).most_common(1)[0][0]
    print(f"ℹ️  Dynamically Identified Standard Cell Row Height: {std_row_height} units\n")
    return node_dimensions, std_row_height

def execute_robust_cluster_filter():
    node_dimensions, std_row_height = analyze_design_components(NODES_FILE)
    
    if not node_dimensions or std_row_height is None:
        print("❌ Failed to parse benchmark geometry. Script aborted.")
        return

    if not os.path.exists(CLUSTERS_FILE):
        print(f"❌ ERROR: Phase 1 clustering file missing at {CLUSTERS_FILE}")
        return

    with open(CLUSTERS_FILE, 'r') as f:
        clusters = json.load(f)

    print("=" * 90)
    print("             PHASE 1 ROBUST MACRO INTEGRITY & FILTERING REPORT              ")
    print("=" * 90)

    total_macros = 0
    total_standard_cells = 0

    # Process cluster by cluster
    for c_id in sorted(clusters.keys(), key=int):
        macros_dict = clusters[c_id]
        
        cluster_macros = []
        cluster_standard_cells = []
        
        for node_name in macros_dict.keys():
            if node_name not in node_dimensions:
                continue
                
            w, h = node_dimensions[node_name]
            area = w * h
            
            # STRENGTHENED DUAL FILTERING LOGIC:
            # An element is classified as a standard cell if:
            # 1. Its footprint area falls strictly in the 4-digit range or lower (<= 9999)
            # OR 2. Its height strictly matches the baseline uniform standard cell row height.
            if area <= 9999 or h == std_row_height:
                cluster_standard_cells.append((node_name, w, h, area))
            else:
                cluster_macros.append((node_name, w, h, area))
                
        total_macros += len(cluster_macros)
        total_standard_cells += len(cluster_standard_cells)
        
        # --- TERMINAL BREAKDOWN PRINT OUT ---
        print(f"\n📦 CLUSTER ID: {c_id}")
        print(f"   ↳ Summary: Found {len(cluster_macros)} True Macros | {len(cluster_standard_cells)} Standard Cells")
        
        # 1. Print True Macros inside this cluster
        if cluster_macros:
            print("   🟢 True Macros Present:")
            for m_name, mw, mh, m_area in sorted(cluster_macros):
                print(f"      • {m_name:<12} [Size: {mw}x{mh}, Area: {m_area:,}]")
        else:
            print("   🟢 True Macros Present: None")
            
        # 2. Explicitly NAME all nodes filtered out as standard cells
        if cluster_standard_cells:
            print("   🔴 Filtered Out Standard Cells:")
            # Combines the cell names into a readable wrapped format
            cell_strings = [f"{name}({w}x{h})" for name, w, h, _ in sorted(cluster_standard_cells)]
            # Print cell names grouped cleanly
            chunks = [cell_strings[x:x+5] for x in range(0, len(cell_strings), 5)]
            for chunk in chunks:
                print("      " + ", ".join(chunk))
        else:
            print("   🔴 Filtered Out Standard Cells: None")
            
        print("-" * 90)

    # Final Execution Summary Dashboard
    print("\n📊 PIPELINE QUALITY INTEGRITY SUMMARY:")
    print("=" * 60)
    print(f"🚀 Total Valid Movable Macros Retained:      {total_macros}")
    print(f"🔒 Total Standard Cells Excluded/Filtered:   {total_standard_cells}")
    print("=" * 60)

if __name__ == "__main__":
    execute_robust_cluster_filter()