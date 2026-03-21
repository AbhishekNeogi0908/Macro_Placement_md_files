# Macro Placement User Manual

### Openroad Downlaod
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
- Steps to use docker environment in VS Code :

  Now, Open VS code and install the "dev container" extension
- Go to terminal and start the container using above mentioned steps. (No need to use 'exec' command)
- Click on ```><``` on the bottom left or Open Command Pallet using ```>``` in search bar.
- Then search for ```Dev Container : Attach running container``` (This will only work if you have started the container, else error)
- Attach the __my_openroad__ container (you should see project directory, which contains the Local mounted directory)
<img width="533" height="51" alt="image" src="https://github.com/user-attachments/assets/95f1b2d9-bf66-41b3-99e4-0eccc4c80510" />

- Now , go to search bar and type ```/``` to move through directories.
- Here,go to project directory now : /project. So ```cd/ prediuous```

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
Probable error: 
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
  
### Manual isntallation using .deb file
  Go to (https://openroad-flow-scripts.readthedocs.io/en/latest/user/BuildWithPrebuilt.html)
  Follow the steps mentioned there
