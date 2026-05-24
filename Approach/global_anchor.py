import json
import os
import numpy as np
import scipy.linalg as la

# Path Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "adaptec1"))
RESULTS_DIR = os.path.join(DATA_DIR, "Results")
CLUSTERS_FILE = os.path.join(RESULTS_DIR, "clustered_macros.json")
PL_FILE = os.path.join(DATA_DIR, "adaptec1.pl")
NETS_FILE = os.path.join(DATA_DIR, "adaptec1.nets")

def load_pl_data(pl_file):
    """Parses the .pl file into a dictionary of {name: (x, y)}."""
    pl_data = {}
    with open(pl_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3 and not line.startswith(('UCLA', '#')):
                pl_data[parts[0]] = (int(parts[1]), int(parts[2]))
    return pl_data

def parse_nets_connectivity(nets_file, clusters):
    """
    Parses the .nets file to calculate explicit inter-cluster wire connectivity weights.
    """
    print("🕸️  Parsing netlist connectivity from .nets file...")
    
    # Map each macro back to its cluster ID for fast lookups
    macro_to_cluster = {}
    for c_id, macros in clusters.items():
        for macro in macros:
            macro_to_cluster[macro] = c_id
            
    cluster_list = list(clusters.keys())
    N = len(cluster_list)
    cluster_to_idx = {c_id: idx for idx, c_id in enumerate(cluster_list)}
    
    # Matrix to store inter-cluster wire connection counts
    C_weights = np.zeros((N, N))
    current_net_clusters = set()
    
    with open(nets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('UCLA', '#')):
                continue
            
            # Detect a new net definition block
            if line.startswith('NetDegree'):
                # Process the previous accumulated net cluster group before starting the new one
                if len(current_net_clusters) > 1:
                    c_indices = [cluster_to_idx[c] for c in current_net_clusters]
                    for i in range(len(c_indices)):
                        for j in range(i + 1, len(c_indices)):
                            u, v = c_indices[i], c_indices[j]
                            C_weights[u][v] += 1
                            C_weights[v][u] += 1
                current_net_clusters = set()
            else:
                # Parse pin lines inside a NetDegree block
                parts = line.split()
                if len(parts) >= 1:
                    macro_name = parts[0]
                    if macro_name in macro_to_cluster:
                        current_net_clusters.add(macro_to_cluster[macro_name])
                        
        # Catch the last net in the file loop
        if len(current_net_clusters) > 1:
            c_indices = [cluster_to_idx[c] for c in current_net_clusters]
            for i in range(len(c_indices)):
                for j in range(i + 1, len(c_indices)):
                    u, v = c_indices[i], c_indices[j]
                    C_weights[u][v] += 1
                    C_weights[v][u] += 1

    return C_weights, cluster_to_idx

def get_centroids(clusters, pl_data):
    """Calculates the center of gravity for each cluster (Baseline mean implementation)."""
    anchors = {}
    for c_id, macros in clusters.items():
        x_coords = []
        y_coords = []
        for name in macros:
            if name in pl_data:
                x_coords.append(pl_data[name][0])
                y_coords.append(pl_data[name][1])
        
        if x_coords:
            anchors[c_id] = {
                "x": int(np.mean(x_coords)),
                "y": int(np.mean(y_coords))
            }
    return anchors

def print_coordinate_comparison(old_anchors, new_anchors):
    """Helper function to print a clean comparison table in the terminal."""
    print("\n📊 COORDINATE SHIFT COMPARISON:")
    print("-" * 75)
    print(f"{'Cluster ID':<15} | {'Old Coordinate (Mean)':<25} | {'New Coordinate (Optimized)':<25}")
    print("-" * 75)
    
    for c_id in sorted(new_anchors.keys()):
        old_x = old_anchors.get(c_id, {}).get('x', 'N/A')
        old_y = old_anchors.get(c_id, {}).get('y', 'N/A')
        new_x = new_anchors[c_id]['x']
        new_y = new_anchors[c_id]['y']
        
        old_str = f"({old_x}, {old_y})"
        new_str = f"({new_x}, {new_y})"
        
        print(f"{c_id:<15} | {old_str:<25} | {new_str:<25}")
    print("-" * 75)

def run_quadratic_spring(clusters, pl_data, nets_file):
    """
    Calculates true global anchor positions using the Quadratic Spring Formulation.
    Constructs an absolute Laplacian Matrix from the parsed .nets connectivity file.
    """
    old_anchors = get_centroids(clusters, pl_data)
    
    C_weights, cluster_to_idx = parse_nets_connectivity(nets_file, clusters)
    
    N = len(cluster_to_idx)
    A = np.zeros((N, N))
    b_x = np.zeros(N)
    b_y = np.zeros(N)
    
    for u in range(N):
        for v in range(N):
            if u != v:
                wire_count = C_weights[u][v]
                A[u][v] = -wire_count
                A[u][u] += wire_count

    for c_id, idx in cluster_to_idx.items():
        if c_id in old_anchors:
            cx = old_anchors[c_id]['x']
            cy = old_anchors[c_id]['y']
            
            gravity_weight = 10.0  
            A[idx][idx] += gravity_weight
            b_x[idx] += gravity_weight * cx
            b_y[idx] += gravity_weight * cy

    print("🧮 Solving parallel linear systems (Ax=b) for X and Y independently...")
    try:
        X_coords = la.solve(A, b_x)
        Y_coords = la.solve(A, b_y)
    except la.LinAlgError:
        print("⚠️ Matrix is singular! Falling back to standard centroid baseline calculation.")
        return old_anchors
        
    new_anchors = {}
    for c_id, idx in cluster_to_idx.items():
        new_anchors[c_id] = {
            "x": int(round(X_coords[idx])),
            "y": int(round(Y_coords[idx]))
        }
        
    print_coordinate_comparison(old_anchors, new_anchors)
    return new_anchors

def run_simulated_annealing(clusters, pl_data):
    """Placeholder for your Phase 3 SA research implementation."""
    old_anchors = get_centroids(clusters, pl_data)
    print("\n🧠 [SA Mode] Initializing Simulated Annealing engine...")
    print("⚠️ Simulated Annealing is currently a stub. Falling back to centroid calculations.")
    
    new_anchors = get_centroids(clusters, pl_data)
    print_coordinate_comparison(old_anchors, new_anchors)
    return new_anchors

if __name__ == "__main__":
    print("=" * 60)
    print("        PHASE 3: GLOBAL ANCHOR PLACEMENT SYSTEM        ")
    print("=" * 60)

    # Validate file dependencies
    if not os.path.exists(CLUSTERS_FILE):
        print(f"❌ ERROR: Clustered macros file not found at: {CLUSTERS_FILE}")
        exit(1)
    if not os.path.exists(PL_FILE):
        print(f"❌ ERROR: Placement layout (.pl) file not found at: {PL_FILE}")
        exit(1)
    if not os.path.exists(NETS_FILE):
        print(f"❌ ERROR: Netlist connection (.nets) file not found at: {NETS_FILE}")
        exit(1)

    print("📂 Loading design database files...")
    with open(CLUSTERS_FILE, 'r') as f:
        clusters = json.load(f)
    pl_data = load_pl_data(PL_FILE)
    print(f"✅ Loaded {len(clusters)} clusters and {len(pl_data)} macro coordinates successfully.")

    # Interactive Terminal Menu Loop
    while True:
        print("\n--- SELECT ANCHOR CALCULATION METHOD ---")
        print("1. Quadratic Spring Formulation (Analytical Placement via .nets)")
        print("2. Simulated Annealing (Heuristic Optimization)")
        print("3. Centroid/Mean Baseline (Legacy Mode)")
        print("4. Exit Program")
        
        choice = input("\nEnter your option (1-4): ").strip()

        if choice == '1':
            print("\n📍 Selected: Quadratic Spring Formulation")
            anchors = run_quadratic_spring(clusters, pl_data, NETS_FILE)
            output_filename = "quadratic_spring_anchors.json"
            break
        elif choice == '2':
            print("\n🔥 Selected: Simulated Annealing")
            anchors = run_simulated_annealing(clusters, pl_data)
            output_filename = "simulated_annealing_anchors.json"
            break
        elif choice == '3':
            print("\n📍 Selected: Centroid Calculation")
            anchors = get_centroids(clusters, pl_data)
            print_coordinate_comparison(anchors, anchors)
            output_filename = "centroid_anchors.json"
            break
        elif choice == '4':
            print("\n👋 Exiting anchor placement workspace.")
            exit(0)
        else:
            print("❌ Invalid selection! Please choose a valid option between 1 and 4.")

    # Build customized path based on the selected execution name
    final_output_path = os.path.join(RESULTS_DIR, output_filename)
    
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(final_output_path, 'w') as f:
        json.dump(anchors, f, indent=4)
        
    print(f"\n💾 Success! Global anchors completely saved to: {final_output_path}")
    print("=" * 60)