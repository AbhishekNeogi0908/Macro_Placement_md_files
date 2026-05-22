# Macro Placement User Manual

## 1. Openroad Downlaod via WSL : 
### Download the wsl ubuntu version 22.04 or 24.04 only.
from Powershell : 
```
wsl --list --online
#then select the ubuntu 22.04 distribution
wsl --install -d Ubuntu-22.04
```
### Working directory for OpenRoad 
In Desktop create a new directory ```Macro_Placement_WSL```
Then proceed for git clone of Openroad / Rosettastone application.
Setup github username profile as well.
### The github for OpenRoad
```
https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/docs/user/Build.md#build-with-prebuilt-binaries
```

### Git Clone Openroad :
- From WSL, do git clone
  ```
  git config --global --add safe.directory "*"
  git clone --recursive https://github.com/The-OpenROAD-Project/OpenROAD.git
  cd OpenROAD
  ```
- Error :
  ```
  git config --global --add safe.directory /project/OpenROAD/third-party/abc
  fatal: Failed to recurse into submodule path 'src/sta'
  fatal: Failed to recurse into submodule path 'third-party/abc'
  ```
  Reason: This "Dubious Ownership" error is a common security feature in newer versions of Git. Since we are working as root inside a Docker container, but the files are being written to a "mounted" directory (your Windows/WSL drive), Git gets suspicious because the file owner on the "outside" doesn't match the user on the "inside."
  Solution 
  ```
  git config --global --add safe.directory "*"
  cd /project/OpenROAD
  git submodule update --init --recursive
  ```
  
### Download the binary file from this website : 
- Go to Official [Direct Download link](https://vaultlink.precisioninno.com/)
- or [Precision website](https://openroad-flow-scripts.readthedocs.io/en/latest/user/BuildWithPrebuilt.html)
- Keep the downloaded binary file into you current project working directory.
- Install it :
  ```
  apt update
  apt install -y ./openroad_26Q1-951-g6975124cf2_amd64-ubuntu-22.04.deb

  # Verify it works
  openroad -version
  ```

OpenRoad successfully Installed !!!
To Open Openroad GUI : ```openroad -gui```
***
## 2. Installing RosettaStone
Since you are already inside your Docker container and positioned in the ```/project``` directory, you can download RosettaStone using git.
```
# 1. Ensure you are in your mounted project folder
cd /project

# 2. Clone the repository
git clone https://github.com/ABKGroup/RosettaStone.git

# 3. Enter the directory to prepare for conversion
cd RosettaStone
```
### RosettaStone env variable path setup - 
Install 'nano' editor (if not installed) :
  ```
  apt install nano
  ```
  Then open .bashrc file :
  ```
  nano ~/.bashrc
  ```
Then add this line at the end of bash file :
  ```
  export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python3.10/dist-packages
  ```
***

## 3. Installing Kahypar 
If you are using Ubuntu 24, the you have to use the argument --break-system-packages, else it will give you virtua environment PEP 668 Error. Or Just create a virtual environment without argument.
#### For ubuntu 24 -
```
pip install kahypar --break-system-packages
```
#### For ubuntu 22 -
```
pip install kahypar
```

**

## 3. Execution 
The file ```BookshelfToOdb.py``` inside ```/project/RosettaStone/benchGen/``` will actually convert the Bookshelf format to Odb format.
There is a driver file name ```run_baseline.py``` which runs the ```BookshelfToOdb.py``` file.
> NOTE : Remove ```odbpy``` from ```BookshelfToOdb.py``` or wherever you see (like import odbpy as odb) because the newer versions don't have anything like odbpy. Just simply ```import odb```
>```
>"/RosettaStone/benchGen/run_BookshelfToOdb.py", line 1, in <module>
>   import odbpy as odb
>   ModuleNotFoundError: No module named 'odbpy'
>```

### To Run 
```  
  openroad -python RosettaStone/benchGen/run_BookshelfToOdb.py 2>&1 | tee conversion_baseline.log
```
All the terminal output / log will be saved in conversion_baseline.log in your current working directory

#### Error 1:
```
"/RosettaStone/benchGen/BookshelfToOdb.py", line 268, in ParseAux
    self.ParseNodes(nodeName)
  File "/RosettaStone/benchGen/BookshelfToOdb.py", line 285, in ParseNodes
    f = open(nodeName, 'r')
FileNotFoundError: [Errno 2] No such file or directory: 'adaptec1.nodes'
```
#### Solution : 
Already added chdir() code in driver program
```
# 2. Teleport the script's execution into your benchmark folder
os.chdir('adaptec1')
```

#### Error 2 : Lef file load error
```
[WARNING ODB-0240] error: Cannot open LEF file ./tech/Nangate45.lef
[INFO ODB-0227] LEF file: ./tech/Nangate45.lef
[ERROR ODB-0289] LEF data from ./tech/Nangate45.lef is discarded due to errors
terminate called after throwing an instance of 'std::runtime_error'
  what():  ODB-0289
Signal 6 received
```
#### Solution :  
There must be path error while loading the tech lef file.
you have hardcode your's tech file path (mounted path) at ```line 13 or 14``` in ```run_BookshelfToOdb.py```

Cross check : 
you can check if Openroad is able to get the lef file.
Open the Openroad CLI from wsl environment.
```
openroad
```
```
read_lef ./tech/Nangate45.lef 
```

#### Error 3: Lef file error 

```
Bookshelf Parsing Done
Traceback (most recent call last):
  File "/project/RosettaStone/benchGen/run_BookshelfToOdb.py", line 17, in <module>
    converter = b2o.BookshelfToOdb(
  File "/project/RosettaStone/benchGen/BookshelfToOdb.py", line 211, in __init__
    self.InitOdb(
  File "/project/RosettaStone/benchGen/BookshelfToOdb.py", line 965, in InitOdb
    chip = self.odbpy.dbChip_create(self.odb)
  File "odb_py.py", line 6345, in dbChip_create
TypeError: Wrong number or type of arguments for overloaded function 'dbChip_create'.
```
Means your Bookshelf files were successfully located and parsed. Your benchmark is officially loaded into memory. The crash you hit next (TypeError: ... dbChip_create) is a classic OpenROAD API version mismatch.In older versions of OpenROAD, you could create a blank "Chip" without defining the physical technology rules first. In OpenROAD 26Q1, the dbChip_create command now strictly requires two arguments: the database and a Technology object (dbTech).

#### Solution : 
#### 1st argument correction
**Direct replacing :** 
Adding the another arg using sed editor using below code from terminal.
```
sed -i 's/chip = self.odbpy.dbChip_create(self.odb)/chip = self.odbpy.dbChip_create(self.odb, self.odb.getTech())/g' /project/RosettaStone/benchGen/BookshelfToOdb.py
```
**Manual Correction :**
1. Open /RosettaStone/benchGen/BookshelfToOdb.py in VS Code.
2. Go to line 965 or nearby where you will see
   ```chip = self.odbpy.dbChip_create(self.odb)```
3. Replace it with : ```chip = self.odbpy.dbChip_create(self.odb, self.odb.getTech())```
4. Save it.

#### 2nd argument correction : 
Here we will add the lef file to RosettaStone.
```
# 1. Create a dedicated folder for your technology files
mkdir -p /project/tech

# 2. Download the official Nangate45 LEF from the OpenROAD repository
wget -O /project/tech/Nangate45.lef https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD/master/test/Nangate45/Nangate45.lef
```
Also the path in driver file have been updated and hardcoded here : 
```
tech_lef = '/tech/Nangate45.lef'
```

#### Try to run again.

#### Error 4: Overwrite Database Units problem in RosettaStone : 

```
Bookshelf Parsing Done
Traceback (most recent call last):
  File "/project/RosettaStone/benchGen/run_BookshelfToOdb.py", line 25, in <module>
    converter = b2o.BookshelfToOdb(
  File "/project/RosettaStone/benchGen/BookshelfToOdb.py", line 211, in __init__
    self.InitOdb(
  File "/project/RosettaStone/benchGen/BookshelfToOdb.py", line 980, in InitOdb
    odbTech.setDbUnitsPerMicron(originalLEFDbu)
AttributeError: 'dbTech' object has no attribute 'setDbUnitsPerMicron'. Did you mean: 'getDbUnitsPerMicron'?
```
On lines ```979``` and ```980``` of BookshelfToOdb.py:
It reads the current Database Units (DBU) from the Nangate45 LEF: originalLEFDbu = ```odbTech.getDbUnitsPerMicron()```
It immediately tries to overwrite the DBU with that exact same number: ```odbTech.setDbUnitsPerMicron(originalLEFDbu)```
In older versions of OpenROAD, this redundant action was harmless. In OpenROAD 26Q1, the developers wisely made the Technology DBU "read-only" once a LEF is loaded. You can't change the fundamental rules of the universe after it's created. 

- So **comment** out this at line 980 or nearby like : 
```
# odbTech.setDbUnitsPerMicron(originalLEFDbu)
````
Try to run again (Mentioned earlier)

#### Error 5:
```
[WARNING] SDFF_X2 has I/O = 4/2, so skipped
Use all masters available in OpenDB: 107 masters
ERROR: Cannot find sequential cells in OpenDB
Traceback (most recent call last):
  File "/project/RosettaStone/benchGen/run_BookshelfToOdb.py", line 35, in <module>
```
#### Solution :
- Go to BookshelfToOdb.py
- Search near line 511 or 514 :
  ```
  ffArr = [0 for m in self.masters if m.isSequential()]

    # if len(ffArr) == 0:
    #   ErrorQuit("Cannot find sequential cells in OpenDB")
  ```
Comment out this above line of code and introduce a dummy ffArr list.
```
# ffArr = [0 for m in self.masters if m.isSequential()]

    # if len(ffArr) == 0:
    #   ErrorQuit("Cannot find sequential cells in OpenDB")
    ffArr = [1]
```

Try to run again. There will be some progress.
```
 openroad -python RosettaStone/benchGen/run_BookshelfToOdb.py 2>&1 | tee conversion_baseline.log
```

#### Error 6: 
```
    self.odbLib = self.odbpy.dbLib_create(self.odb, "fakeMacros")
  File "odb_py.py", line 4340, in dbLib_create
TypeError: Wrong number or type of arguments for overloaded function 'dbLib_create'.
  Possible C/C++ prototypes are:
    odb::dbLib::create(odb::dbDatabase *,char const *,odb::dbTech *,char)
    odb::dbLib::create(odb::dbDatabase *,char const *,odb::dbTech *)
```

#### Solution : 
Due to new version, it is another API mismatch. Just like the "Chip" creation error we fixed earlier, the OpenROAD 26Q1 version of dbLib_create now strictly requires you to pass the Technology object (dbTech) when creating a new library.

**Manual Update :** 
1. Open /project/RosettaStone/benchGen/BookshelfToOdb.py.
2. Go to Line 1242.
3. Change: ```self.odbLib = self.odbpy.dbLib_create(self.odb, "fakeMacros")```
4. To: ```self.odbLib = self.odbpy.dbLib_create(self.odb, "fakeMacros", self.odb.getTech())```
5. Save the file.

#### Error 6 : 
```
 File "/project/RosettaStone/benchGen/BookshelfToOdb.py", line 1445, in FillOdbNets
    self.odbpy.dbITerm_connect(dbITerm, dbNet)
AttributeError: module 'odb' has no attribute 'dbITerm_connect'. Did you mean: 'dbCCSeg_connect'?
```
This AttributeError is the final hurdle in the API migration. In OpenROAD 26Q1, the dbITerm_connect function was moved from a standalone module function to a direct method of the dbITerm object.
#### Solution : 
**Terminal command to edit :** 
```
sed -i 's/self.odbpy.dbITerm_connect(dbITerm, dbNet)/dbITerm.connect(dbNet)/g' /project/RosettaStone/benchGen/BookshelfToOdb.py
```

**Manual Edit (Recommended):**

1. Open ```/project/RosettaStone/benchGen/BookshelfToOdb.py.```
2. Go to Line 1445.
3. Change: ```self.odbpy.dbITerm_connect(dbITerm, dbNet)```
4. To: ```dbITerm.connect(dbNet)```
5. Save the file.

Try to run : ```openroad -python /project/RosettaStone/benchGen/run_BookshelfToOdb.py 2>&1 | tee conversion_baseline.log ```

**

## 4. Expected Output 
```Success! Baseline created at ./adaptec1/odbFiles/adaptec1_baseline.odb```

You will get the odb file inside ```Macro_Placement_WSL/adaptec1/odbFiles/adaptec1_baseline.odb```

**
## Openroad baseline section

**

Our Approach :

### Phase 1 : Partitioning
Is done by ```partition_macros.py``` script.
From ```Macro_Placement_WSL``` navigate to ```Approach``` directory.

```
cd Approach
python3 partition_macros.py
```
Expected output : ```clustered_macros.json``` should appear in ```adaptec1/Results/```

### Phase 2: Global Anchor calculation 
This uses the clustered results to calculate the center of gravity for each cluster.

```
python3 global_anchor.py --mode centroid
```
Expected Output: ```cluster_anchors.json``` should appear in ```adaptec1/Results/```

### Phase 3: Macro Optimization (Gurobi)
This is where the heavy mathematical optimization happens.

```
python3 optimize_macros.py
```

Expected Output: ```optimized_macros.json``` should appear in ```adaptec1/Results/```

### Phase 4: Integration
This takes your baseline .pl file and "injects" the optimized coordinates.

```
python3 re_intregrate_placement.py
```
Expected Output: ```Merged_optimized.pl``` should be generated in ```adaptec1/Results/```

#### Important Notes to Ensure Success:
Run from Approach/: Do not run these scripts from the Macro_Placement_WSL root or the adaptec1 folder. If you run them from the wrong place, the .. in the file paths will point to the wrong location, and the script will fail to find adaptec1.nodes or adaptec1.pl.

#### Dependencies:
Ensure Gurobi is active/installed, as optimize_macros.py relies on gurobipy.

#### Standard Cell Handling: 
Your re_intregrate_placement.py script now handles standard cells by marking them : N (movable) while respecting the fixed status of IO pads. If you get parser errors in OpenROAD later, it means there are still nodes in your .pl file incorrectly marked as /FIXED that OpenROAD doesn't recognize as terminals. The log output shows FIXED for macros, which is correct; if you see FIXED for a standard cell (non-macro), that cell needs its tag removed in the .pl file.
