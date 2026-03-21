# Macro Placement User Manual

## Openroad Downlaod
1. Docker Download
We will downlad and use openroad using wsl. So Here are the steps to download Openroad in wsl and then run it in VS Code.
```
sudo apt udpate
sudo apt install docker.io
```
Pull the predefined docker image of Openroad using docker : 
```
sudo docker pull openroad/ubuntu20.04-dev
```
> **Note** : To get all container details type ``` sudo docker ps -a ```
> or ``` sudo docker images ```

To start using docker's openroad image you can type :
- First start the docker service (docker daemon)
- Then create + run and new container name "my_openroad" along with our project mounted.
```
sudo service docker start

# First time only
sudo docker run -dt --name my_openroad -v "${PWD}:/project" openroad/ubuntu20.04-dev
```
Open a pre-made container (example container name 'my_openroad') : 
```
# 1. Start the existing container
sudo docker ps -as
sudo docker start my_openroad

# 2. "Step into" the already running container
sudo docker exec -it my_openroad bash
```
*! MOST PROBABLY YOU ARE INSIDE the Openraod Docker environment !*
>- Type ```exit``` to exit from docker environment.
>- Type ```sudo docker ps -as``` to check all container details.
>- Type ```sudo service docker status``` to check the status of docker (running or stopped).
>- Type ```sudo docker stop my_openroad ``` to stop the running container.
>- Type ```sudo service docker stop``` to stop the full docker service.

### Docker container in VS Code
Steps to use docker environment in VS Code. Now, Open VS code and install the "dev container" extension. Then do the following :
- Go to terminal and start the container using above/below mentioned steps.
  ```
  sudo docker ps -as
  sudo docker start my_openroad
  # No need to use 'docker exec' command
  ```
- Click on ```><``` on the bottom left or Open Command Pallet using ```>``` in search bar.
- Then search for ```Dev Container : Attach running container``` (This will only work if you have started the container, else error)
- Attach the __my_openroad__ container (you should see project directory, which contains the Local mounted directory)
<img width="533" height="51" alt="image" src="https://github.com/user-attachments/assets/95f1b2d9-bf66-41b3-99e4-0eccc4c80510" />

- Now , go to search bar and type ```/``` to move through directories.
- Here,go to project directory now : /project.

  ***
  
### The github for OpenRoad
```
https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/docs/user/Build.md#build-with-prebuilt-binaries
```
### Git Clone Openroad :
- From the docker or simple wsl, do git clone
  ```
  git config --global --add safe.directory "*"
  git clone --recursive https://github.com/The-OpenROAD-Project/OpenROAD.git
  cd OpenROAD
  ```
- Probable error:
  ```
  git config --global --add safe.directory /project/OpenROAD/third-party/abc
  fatal: Failed to recurse into submodule path 'src/sta'
  fatal: Failed to recurse into submodule path 'third-party/abc'
  ```
  Reason: This "Dubious Ownership" error is a common security feature in newer versions of Git. Since you are working as root inside a Docker container, but the files are being written to a "mounted" directory (your Windows/WSL drive), Git gets suspicious because the file owner on the "outside" doesn't match the user on the "inside."
  Solution 
  ```
  git config --global --add safe.directory "*"
  cd /project/OpenROAD
  git submodule update --init --recursive
  ```
### Download the binary file from this website : 
- Go to Official [Precision website](https://openroad-flow-scripts.readthedocs.io/en/latest/user/BuildWithPrebuilt.html) 
- Keep the downloaded binary file into you current project working directory.
- Install it (via docker environment) :
  ```
  apt update
  apt install -y /project/openroad_26Q1-951-g6975124cf2_amd64-ubuntu-22.04.deb

  # Verify it works
  openroad -version
  ```

OpenRoad successfully Installed !!!

***
## Installing RosettaStone
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

### Create Symbolic link 
Since we are working in a Docker container with limited virtual disk space, we don't want to have three copies of the adaptec1 benchmark (one in your root, one in RosettaStone, one in your Optimizer folder).
```
# ln -s [TARGET_FOLDER] [LINK_NAME]
ln -s /project/adaptec1 ./adaptec1
```
To verify symbolic link :  
```
ls -l
```
Expected output : something like :```lrwxrwxrwx 1 1000 1000    17 Mar 21 03:41 adaptec1 -> /project/adaptec1```

***

### Execution 
The file ```BookshelfToOdb.py``` inside ```/project/RosettaStone/benchGen/``` will actually convert the Bookshelf format to Odb format.
There is a driver file name ```run_baseline.py``` which runs the ```BookshelfToOdb.py``` file.
> NOTE : Remove ```odbpy``` from ```BookshelfToOdb.py``` or wherever you see (like import odbpy as odb) because the newer versions don't have anything like odbpy. Just simply ```import odb```
>```
>"/project/RosettaStone/benchGen/run_BookshelfToOdb.py", line 1, in <module>
>   import odbpy as odb
>   ModuleNotFoundError: No module named 'odbpy'
>```

###To Run :
```
 openroad -python /project/RosettaStone/benchGen/run_BookshelfToOdb.py
```

#### Error 1:
```
"/project/RosettaStone/benchGen/BookshelfToOdb.py", line 268, in ParseAux
    self.ParseNodes(nodeName)
  File "/project/RosettaStone/benchGen/BookshelfToOdb.py", line 285, in ParseNodes
    f = open(nodeName, 'r')
FileNotFoundError: [Errno 2] No such file or directory: 'adaptec1.nodes'
```
#### Solution : 
Already added chdir() code in driver program
```
# 2. Teleport the script's execution into your benchmark folder
os.chdir('/project/adaptec1')
```
Error 2: Lef file error 
Means your Bookshelf files were successfully located and parsed. Your benchmark is officially loaded into memory. The crash you hit next (TypeError: ... dbChip_create) is a classic OpenROAD API version mismatch.In older versions of OpenROAD, you could create a blank "Chip" without defining the physical technology rules first. In OpenROAD 26Q1, the dbChip_create command now strictly requires two arguments: the database and a Technology object (dbTech).

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
#### Solution : 
#### 1st argument correction
**Direct replacing :** 
Adding the another arg using sed editor using below code from terminal.
```
sed -i 's/chip = self.odbpy.dbChip_create(self.odb)/chip = self.odbpy.dbChip_create(self.odb, self.odb.getTech())/g' /project/RosettaStone/benchGen/BookshelfToOdb.py
```
**Manual Correction :**
1. Open /project/RosettaStone/benchGen/BookshelfToOdb.py in VS Code.
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
Also the path in driver file have been updated and hardcoded here : ```tech_lef = '/project/tech/Nangate45.lef'```
Error 3: Overwrite Database Units problem in RosettaStone : 

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

- So **comment** out this at line980 or nearby. 
```
odbTech.setDbUnitsPerMicron(originalLEFDbu)
````
Try to run again (Mentioned earlier)

