#FROM tensorflow/tensorflow:nightly-devel-gpu-py3
FROM debian:buster-slim
#FROM ubuntu:latest

WORKDIR /home
ENV HOME /home
VOLUME /data
EXPOSE 8888
RUN cd ~

RUN apt-get update
RUN apt-get install -y software-properties-common curl python3-pip
RUN apt-get install -y python3-requests python3-urllib3

RUN apt-get install -y build-essential libpython3-dev  libusb-1.0-0-dev vim feh x11-apps apt-utils

###RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
#RUN apt-get update
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" \
    | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

RUN apt-get update
RUN apt-get install -y git nano python-pip python-dev pkg-config wget usbutils
#RUN apt-get upgrade -y gcc-4.9 libstdc++6 vim


#RUN apt-get install -y libedgetpu1-std
RUN echo "libedgetpu1-max libedgetpu/accepted-eula boolean true" | debconf-set-selections && apt-get install -y libedgetpu1-max
#RUN DEBIAN_FRONTEND=noninteractive apt-get install -y libedgetpu1-max
#RUN apt-get install -y edgetpu-compiler
#RUN apt-get install -y edgetpu 
RUN apt-get install -y python3-edgetpu
##RUN apt-get install -y python3-coral-enviro
RUN apt-get install -y edgetpu-examples
#RUN apt-get install -y libedgetpu-dev


#RUN wget https://dl.google.com/coral/python/tflite_runtime-1.14.0-cp35-cp35m-linux_x86_64.whl
#RUN pip3 install tflite_runtime-1.14.0-cp35-cp35m-linux_x86_64.whl
RUN wget https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl
RUN pip3 install tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl

RUN mkdir coral && cd coral
RUN git clone https://github.com/google-coral/tflite.git
#RUN cd
#RUN cd tflite/python/examples/classification
#RUN bash ./install_requirements.sh


RUN cd
RUN git clone https://github.com/google-coral/edgetpu.git
RUN bash /home/tflite/python/examples/classification/install_requirements.sh


# DeepPiCar
RUN git clone https://github.com/dctian/DeepPiCar.git


RUN apt-get install -y libhdf5-dev libhdf5-serial-dev libatlas-base-dev libqtgui4 libqt4-test
#RUN apt-get install -y libjasper-dev
RUN pip3 install opencv-python
RUN pip3 install matplotlib
RUN pip3 install paho-mqtt

RUN cp /usr/share/edgetpu/examples/models/* /home/tflite/python/examples/classification/models/.
RUN cp /usr/share/edgetpu/examples/images/* /home/tflite/python/examples/classification/images/.

RUN mkdir detection
CMD ["bash", "-c", "sh ./detection/run.sh"]
