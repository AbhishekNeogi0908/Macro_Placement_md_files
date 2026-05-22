
import sys
import os
from pathlib import Path

# Step 1: Dynamically locate the 'Macro_Placement' directory path
# This looks at the absolute path of this file and climbs up to find 'Macro_Placement'
current_path = Path(os.path.abspath(__file__))
macro_placement_dir = next(p for p in current_path.parents if p.name == "Macro_Placement")

# 1. Setup paths
sys.path.append(macro_placement_dir / 'RosettaStone' / 'benchGen')
import odb
import BookshelfToOdb as b2o

# 2. Ask user for mode
mode = input("Enter mode (baseline / optimized): ").strip().lower()

if mode == "baseline":
    aux_file = "adaptec1.aux"
    tag = "baseline"
elif mode == "optimized":
    aux_file = "optimized_adaptec1.aux"
    tag = "optimized"
else:
    print("Invalid mode! Use 'baseline' or 'optimized'")
    sys.exit(1)

# 3. Change directory
os.chdir('adaptec1')

# 4. Create database
db = odb.dbDatabase.create()

# 5. Read technology LEF
# tech_lef = '/mnt/c/Users/abhis/OneDrive/Desktop/Macro_Placement_WSL/tech/Nangate45.lef'
tech_lef = os.path.join(macro_placement_dir, 'tech', 'Nangate45.lef')
print(f"Loading Technology LEF: {tech_lef}")
odb.read_lef(db, tech_lef)

# 6. Detect site name
site_name = "FreePDK45_38x28_10R_NP_162NW_34O"
libs = db.getLibs()

if libs:
    for lib in libs:
        sites = lib.getSites()
        if sites:
            site_name = sites[0].getName()
            break

print(f"Auto-detected Site Name: {site_name}")

# 7. Run Bookshelf conversion
converter = b2o.BookshelfToOdb(
    opendbpy=odb,
    opendb=db,
    auxName=aux_file,   # <-- dynamic now
    siteName=site_name,
    ffClkPinList=['CLK'],
    customFPRatio=1.0
)

# 8. Output folder
output_dir = "odbFiles"
os.makedirs(output_dir, exist_ok=True)

# 9. Save ODB
odb_path = os.path.join(output_dir, f"adaptec1_{tag}.odb")
odb.write_db(db, odb_path)

# 10. Save DEF
block = db.getChip().getBlock()
def_path = os.path.join(output_dir, f"adaptec1_{tag}.def")
odb.write_def(block, def_path)

# 11. Save LEF
libs = db.getLibs()
print(f"DEBUG: Found {len(libs)} libraries in database.")
for lib in libs:
    print(f"DEBUG: Found library: {lib.getName()}")

for lib in db.getLibs():
    lef_path = os.path.join(output_dir, f"{lib.getName()}")
    odb.write_lef(lib, lef_path)
    print(f"Generated LEF: {lef_path}")

print("\nSUCCESS!")
print(f"ODB: {odb_path}")
print(f"DEF: {def_path}")