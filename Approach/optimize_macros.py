import json
import os
import sys
from gurobipy import Model, GRB, quicksum

# Path Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "adaptec1"))
RESULTS_DIR = os.path.join(DATA_DIR, "Results")

JSON_IN = os.path.join(RESULTS_DIR, "clustered_macros.json")
JSON_OUT = os.path.join(RESULTS_DIR, "optimized_macros.json")
NODES_FILE = os.path.join(DATA_DIR, "adaptec1.nodes")  # Source for macro widths and heights

def select_anchor_file():
    """
    Displays an interactive menu to choose the global anchor file type 
    generated from Phase 3. Returns the full absolute path of the chosen file.
    """
    print("=" * 60)
    print("         PHASE 4: INTRA-CLUSTER OPTIMIZATION SYSTEM       ")
    print("=" * 60)
    
    while True:
        print("\n--- SELECT GLOBAL ANCHOR METHOD FOR OPTIMIZATION ---")
        print("1. Quadratic Spring Formulation  (quadratic_spring_anchors.json)")
        print("2. Simulated Annealing           (simulated_annealing_anchors.json)")
        print("3. Centroid/Mean Baseline        (centroid_anchors.json)")
        print("4. Legacy Default Anchor System  (cluster_anchors.json)")
        print("5. Abort Optimization")
        
        choice = input("\nEnter your option (1-5): ").strip()
        
        if choice == '1':
            filename = "quadratic_spring_anchors.json"
            break
        elif choice == '2':
            filename = "simulated_annealing_anchors.json"
            break
        elif choice == '3':
            filename = "centroid_anchors.json"
            break
        elif choice == '4':
            filename = "cluster_anchors.json"
            break
        elif choice == '5':
            print("\n👋 Optimization workspace aborted.")
            sys.exit(0)
        else:
            print("❌ Invalid selection! Please choose a valid option between 1 and 5.")
            
    selected_path = os.path.join(RESULTS_DIR, filename)
    
    if not os.path.exists(selected_path):
        print(f"\n❌ ERROR: The file '{filename}' was not found in your Results directory!")
        print("💡 Please make sure you have executed Phase 3 using that specific method first.")
        sys.exit(1)
        
    print(f"\n🎯 Successfully loaded anchor roadmap: {filename}")
    return selected_path

def load_macro_dimensions(nodes_file):
    """
    Parses the standard UCLA bookshelf .nodes file format.
    Extracts the width and height dimensions for every macro node.
    """
    dimensions = {}
    if not os.path.exists(nodes_file):
        print(f"❌ ERROR: {nodes_file} not found! Cannot extract macro dimensions.")
        sys.exit(1)
        
    print("📐 Extracting physical dimensions from .nodes file...")
    with open(nodes_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('UCLA', '#', 'NumNodes', 'NumTerminals')):
                continue
            parts = line.split()
            if len(parts) >= 3:
                node_name = parts[0]
                try:
                    w = int(parts[1])
                    h = int(parts[2])
                    dimensions[node_name] = (w, h)
                except ValueError:
                    continue
    return dimensions

def optimize_cluster(c_id, macros_dict, anchor, time_seconds, macro_sizes):
    """
    Optimizes the layout placement of individual macro string identifiers 
    within a single cluster boundary using a Gurobi Mixed-Integer Linear Program.
    """
    # FIX: Convert the cluster dictionary keys into a clean indexable list of string names
    macro_names = list(macros_dict.keys())
    num_macros = len(macro_names)
    
    if num_macros == 0:
        return []

    # 1. Instantiate the Solver Environment
    model = Model(f"Cluster_{c_id}_Optimization")
    model.setParam('OutputFlag', 1)  # Silence heavy Gurobi logging output
    model.setParam('TimeLimit', time_seconds)  # Force execution time ceiling
    
    anchor_x = anchor["x"]
    anchor_y = anchor["y"]
    
    # 2. Establish Spatial Bounding Boxes (+/- 1500 units padding around anchor)
    MARGIN = 1500
    BB_MIN_X, BB_MAX_X = anchor_x - MARGIN, anchor_x + MARGIN
    BB_MIN_Y, BB_MAX_Y = anchor_y - MARGIN, anchor_y + MARGIN
    
    x_vars = {}
    y_vars = {}
    
    # 3. Formulate decision coordinates for the bottom-left vertex of each macro block
    for m_name in macro_names:
        w, h = macro_sizes.get(m_name, (100, 100))  # Safe fallback size default
        
        x_vars[m_name] = model.addVar(lb=BB_MIN_X, ub=BB_MAX_X - w, vtype=GRB.CONTINUOUS, name=f"x_{m_name}")
        y_vars[m_name] = model.addVar(lb=BB_MIN_Y, ub=BB_MAX_Y - h, vtype=GRB.CONTINUOUS, name=f"y_{m_name}")
        
    # 4. Generate Linear Absolute Displacement Variables for wire-length proxy minimization
    dx_vars = {}
    dy_vars = {}
    for m_name in macro_names:
        dx_vars[m_name] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"dx_{m_name}")
        dy_vars[m_name] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"dy_{m_name}")
        
        # Convex linearization bounds: dx >= |x - anchor_x|
        model.addConstr(dx_vars[m_name] >= x_vars[m_name] - anchor_x)
        model.addConstr(dx_vars[m_name] >= anchor_x - x_vars[m_name])
        
        model.addConstr(dy_vars[m_name] >= y_vars[m_name] - anchor_y)
        model.addConstr(dy_vars[m_name] >= anchor_y - y_vars[m_name])

    # 5. Overlap Prevention via a Big-M Formulation (Legalization)
    BIG_M = 40000  
    
    for i in range(num_macros):
        for j in range(i + 1, num_macros):
            name1 = macro_names[i]
            name2 = macro_names[j]
            
            w1, h1 = macro_sizes.get(name1, (100, 100))
            w2, h2 = macro_sizes.get(name2, (100, 100))
            
            # Topological binary direction switches
            b_left  = model.addVar(vtype=GRB.BINARY, name=f"b_left_{name1}_{name2}")
            b_right = model.addVar(vtype=GRB.BINARY, name=f"b_right_{name1}_{name2}")
            b_below = model.addVar(vtype=GRB.BINARY, name=f"b_below_{name1}_{name2}")
            b_above = model.addVar(vtype=GRB.BINARY, name=f"b_above_{name1}_{name2}")
            
            # Require at least one boundary edge condition to eliminate overlaps
            model.addConstr(b_left + b_right + b_below + b_above >= 1)
            
            # Enforce spatial clearance constraints based on active topology switches
            model.addConstr(x_vars[name1] + w1 <= x_vars[name2] + BIG_M * (1 - b_left))
            model.addConstr(x_vars[name2] + w2 <= x_vars[name1] + BIG_M * (1 - b_right))
            model.addConstr(y_vars[name1] + h1 <= y_vars[name2] + BIG_M * (1 - b_below))
            model.addConstr(y_vars[name2] + h2 <= y_vars[name1] + BIG_M * (1 - b_above))

    # 6. Set Objective Function: Minimize displacement sum
    total_displacement = quicksum(dx_vars[m_name] + dy_vars[m_name] for m_name in macro_names)
    model.setObjective(total_displacement, GRB.MINIMIZE)
    
    # 7. Run Optimization
    model.optimize()
    
    # 8. Extract Coordinates and Construct Output Geometry List
    optimized_macros = []
    if model.status == GRB.OPTIMAL or model.status == GRB.TIME_LIMIT:
        for m_name in macro_names:
            w, h = macro_sizes.get(m_name, (100, 100))
            optimized_macros.append({
                "macro_id": m_name,
                "x": int(round(x_vars[m_name].X)) if hasattr(x_vars[m_name], 'X') else int(anchor_x),
                "y": int(round(y_vars[m_name].X)) if hasattr(y_vars[m_name], 'X') else int(anchor_y),
                "width": w,
                "height": h
            })
    else:
        print(f"⚠️ Warning: Cluster {c_id} optimization failed. Stacking components directly on anchor.")
        for m_name in macro_names:
            w, h = macro_sizes.get(m_name, (100, 100))
            optimized_macros.append({
                "macro_id": m_name,
                "x": int(anchor_x),
                "y": int(anchor_y),
                "width": w,
                "height": h
            })
            
    return optimized_macros


if __name__ == "__main__":
    # Validate raw numerical time argument signature from execution terminal
    if len(sys.argv) < 2:
        print("❌ ERROR: Please provide the execution time ceiling (in seconds) as a terminal argument.")
        print("Usage: python optimize_macros.py <time_in_seconds>")
        sys.exit(1)

    try:
        time_seconds = float(sys.argv[1])
    except ValueError:
        print(f"❌ ERROR: '{sys.argv[1]}' is not a valid timeout limit number.")
        sys.exit(1)

    # Trigger anchor selection prompt box
    json_anchors_path = select_anchor_file()

    # Structural path cross-check assertions
    if not os.path.exists(JSON_IN):
        print(f"❌ ERROR: Clustered macros configuration file missing! Check path: {JSON_IN}")
        sys.exit(1)

    # Load file contents
    print("\n📂 Loading input layout databases...")
    with open(JSON_IN, 'r') as f: 
        clusters = json.load(f)
    with open(json_anchors_path, 'r') as f: 
        anchors = json.load(f)
        
    # Dynamically extract widths and heights directly from benchmark dataset source
    macro_sizes = load_macro_dimensions(NODES_FILE)
    print(f"✅ Successfully cached layout dimensions for {len(macro_sizes)} design components.")

    print(f"⏱️  Intra-cluster optimization active. Cluster solver window limit: {time_seconds} seconds\n")

    optimized_clusters = {}

    # Run macro legalization cluster-by-cluster
    for c_id, macros_dict in clusters.items():
        if c_id in anchors:
            print(f"🔧 Optimizing Cluster {c_id:^5} via Gurobi MILP Framework...")
            optimized_clusters[c_id] = optimize_cluster(c_id, macros_dict, anchors[c_id], time_seconds, macro_sizes)
    
    # Export results out into standard Results tree directory
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(JSON_OUT, 'w') as f:
        json.dump(optimized_clusters, f, indent=4)
        
    print(f"\n💾 Success! Finalized macro placement floorplan mapped directly to: {JSON_OUT}")
    print("=" * 60)