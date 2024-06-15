FROM ultralytics/ultralytics:8.2.32-jetson-jetpack4

ARG DEBIAN_FRONTEND=noninteractive
ARG IMGSZ='(192,512)'

WORKDIR /traffic

RUN apt-get install python3-tk -y

RUN yolo export model=yolov8m.pt format=engine device=0 workspace=1 simplify=true imgsz="${IMGSZ}"
RUN pip3 install shapely==2.0.4 lapx==0.5.9

COPY . /traffic


ENTRYPOINT [ "python3", "detect.py" ]