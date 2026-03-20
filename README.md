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
```
sudo service docker start
sudo docker run -it openroad/ubuntu20.04-dev
```
> Type ```sudo service docker status``` to check the status of docker (running or stopped)
> Type ```exit``` to exit from docker environment.
> Type ```sudo docker stop ``` to stop the running container.
> Type ``` sudo service docker stop``` to stop the full docker service.

Now to mount the current macro placement project directory and run docker :
```
sudo docker run -dt -v $(pwd):/project openroad/ubuntu20.04-dev
```



- Steps to use docker environment in VS Code :

  Now, Open VS code and install the "dev container" extension
- Go to terminal and start the container : 

