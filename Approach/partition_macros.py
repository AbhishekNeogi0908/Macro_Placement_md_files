import json
import os
import sys
import kahypar
import urllib.request
from collections import Counter

# ==========================================
# Path Configuration
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "adaptec1"))
RESULTS_DIR = os.path.join(DATA_DIR, "Results")
PHASE1_DIR = RESULTS_DIR

os.makedirs(PHASE1_DIR, exist_ok=True)

NODES_FILE = os.path.join(DATA_DIR, "adaptec1.nodes")
PL_FILE    = os.path.join(DATA_DIR, "adaptec1.pl")
NETS_FILE  = os.path.join(DATA_DIR, "adaptec1.nets")
JSON_OUT   = os.path.join(PHASE1_DIR, "clustered_macros.json")

def verify_files_exist():
    missing = [f for f in [NODES_FILE, PL_FILE, NETS_FILE] if not os.path.exists(f)]
    if missing:
        print("❌ ERROR: Could not find the following files:")
        for m in missing: print(f"   - {m}")
        sys.exit(1)
    print("✅ All Bookshelf files found successfully!")

def get_kahypar_config():
    ini_path = os.path.join(PHASE1_DIR, "cut_kKaHyPar_sea20.ini")
    if not os.path.exists(ini_path):
        print("📥 Downloading official KaHyPar configuration file...")
        url = "https://raw.githubusercontent.com/kahypar/kahypar/master/config/cut_kKaHyPar_sea20.ini"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(ini_path, 'wb') as out_file:
                out_file.write(response.read())
            print("✅ Configuration downloaded successfully.")
        except Exception as e:
            print(f"❌ Failed to download configuration: {e}")
            sys.exit(1)
    return ini_path

def parse_bookshelf(nodes_file, pl_file, nets_file, max_fanout=500):
    """Dynamically extracts and purifies macros based on dynamic row profiling."""
    macros = {}
    macro_names = []
    hyperedges = []
    
    all_raw_nodes = {}
    all_heights = []
    
    # ---------------------------------------------------------
    # PASS 1: Read database and dynamically find cell row height
    # ---------------------------------------------------------
    with open(nodes_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3 and not line.startswith(('UCLA', 'Num', '#')):
                name, w, h = parts[0], int(parts[1]), int(parts[2])
                is_fixed = (len(parts) > 3 and parts[3] == 'terminal')
                
                all_raw_nodes[name] = {"w": w, "h": h, "fixed": is_fixed, "x": 0, "y": 0}
                if not is_fixed:
                    all_heights.append(h)

    std_cell_height = Counter(all_heights).most_common(1)[0][0] if all_heights else 12
    print(f"ℹ️  Dynamically Identified Standard Cell Row Height: {std_cell_height} units")

    # ---------------------------------------------------------
    # PASS 2: Explicit Purification Filtering Matrix
    # ---------------------------------------------------------
    dropped_cells = 0
    
    for name, data in all_raw_nodes.items():
        w, h, originally_fixed = data['w'], data['h'], data['fixed']
        area = w * h
        
        # THE EXACT AUDIT LOGIC GATING MECHANISM:
        # If an item's area is 4-digits or less, OR its height matches the uniform row height,
        # it is classified as a standard cell. Drop/remove it completely!
        if area <= 9999 or h == std_cell_height:
            dropped_cells += 1
            continue
            
        # If it survives the gate, it is a True Macro.
        # Un-fix if it was a movable macro, otherwise retain its fixed anchor status.
        is_hard_fixed = originally_fixed
        macros[name] = {"w": w, "h": h, "fixed": is_hard_fixed, "x": 0, "y": 0}
        macro_names.append(name)

    print(f"🔒 Safely identified and dropped {dropped_cells} standard cells before partitioning.")

    print("Parsing .pl...")
    with open(pl_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3 and not line.startswith(('UCLA', '#')):
                name = parts[0]
                if name in macros:
                    macros[name]['x'] = int(parts[1])
                    macros[name]['y'] = int(parts[2])

    print("Parsing .nets...")
    with open(nets_file, 'r') as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('NetDegree'):
            degree = int(line.split(':')[1].strip().split()[0])
            if degree <= max_fanout:
                current_net = []
                for _ in range(degree):
                    i += 1
                    node_name = lines[i].strip().split()[0]
                    if node_name in macros:
                        current_net.append(node_name)
                
                unique_net = list(set(current_net))
                if len(unique_net) >= 2:
                    hyperedges.append(unique_net)
            else:
                i += degree
        i += 1

    return macros, macro_names, hyperedges

def partition_with_kahypar(macros, macro_names, hyperedges, k=40, epsilon=0.03):
    print(f"\n🚀 Starting KaHyPar in-memory partitioning (Clusters = {k})...")
    
    name_to_id = {name: idx for idx, name in enumerate(macro_names)}
    num_nodes = len(macro_names)
    num_edges = len(hyperedges)
    
    edge_indices = [0]
    edges_flat = []
    
    for edge in hyperedges:
        for name in edge:
            edges_flat.append(name_to_id[name])
        edge_indices.append(len(edges_flat))
        
    node_weights = [1] * num_nodes
    edge_weights = [1] * num_edges
    
    hypergraph = kahypar.Hypergraph(
        num_nodes, num_edges, edge_indices, edges_flat, k, edge_weights, node_weights
    )
    
    context = kahypar.Context()
    ini_path = get_kahypar_config()
    context.loadINIconfiguration(ini_path)
        
    context.setK(k)
    context.setEpsilon(epsilon)
    context.suppressOutput(True)
    
    print("🧠 Partitioning engine running...")
    kahypar.partition(hypergraph, context)
    
    clusters = {str(i): {} for i in range(k)}
    for name in macro_names:
        node_id = name_to_id[name]
        block_id = hypergraph.blockID(node_id)
        clusters[str(block_id)][name] = macros[name]
        
    return clusters

if __name__ == "__main__":
    verify_files_exist()

    MACROS, MACRO_NAMES, HYPEREDGES = parse_bookshelf(
        NODES_FILE, PL_FILE, NETS_FILE,
        max_fanout=500
    )
    
    print(f"\n📊 Extraction Summary:")
    print(f"   - Found {len(MACROS)} Real Macros/Fixed Pads")
    print(f"   - Found {len(HYPEREDGES)} valid Macro-to-Macro nets")

    FINAL_CLUSTERS = partition_with_kahypar(MACROS, MACRO_NAMES, HYPEREDGES, k=40)
    
    with open(JSON_OUT, 'w') as f:
        json.dump(FINAL_CLUSTERS, f, indent=4)
        
    print(f"\n✅ Successfully grouped macros into {len(FINAL_CLUSTERS)} clusters with zero standard cells.")
    print(f"Saved to: {JSON_OUT}\n")