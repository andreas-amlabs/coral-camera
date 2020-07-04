# coral-camera
Edge TPU process multiple camera streams

This is how I run the test program
DISPLAY is not really necessary as images are posted
on the MQTT bus. It is however useful for debug purposes

DISPLAY=1.2.3.4:0 docker run -it --privileged -v /dev:/dev -v ./coral/code:/home/code -v /tmp/.X11-unix:/tmp/.X11-unix -v ~/.Xauthority:/home/.Xauthority -e DISPLAY=$DISPLAY --hostname <HOST> --net host coral-test bash
