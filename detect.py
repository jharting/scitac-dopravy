from ultralytics import YOLO
from ultralytics.solutions import object_counter
from utils import FrameDropDecorator, ShutdownHandler
import cv2
import datetime
import os
import numpy
import yaml
import argparse

def parseConfig(path):
    with open(path, 'r') as file:
        config = yaml.safe_load(file)

        # transform coordinates to tuples
        config['region_points'] = [tuple(i) for i in config['region_points']]

        return config

def crop(frame, crop_config):
    for axis, regions in enumerate(crop_config):
        for region in regions:
            frame = numpy.delete(frame, slice(region[0], region[1]), axis)
    return frame

def store_hit(frame, config):
    now = datetime.datetime.now()
    dir = os.path.join(config['workdir'], now.strftime("%Y-%m-%d"))
    if not os.path.exists(dir):
        os.mkdir(dir, 0o755)

    prefix = now.strftime("%Y-%m-%dT%H:%M:%S.%f")

    if config['store_frame']:
        path = os.path.join(dir, "%s.%s" % (prefix, "jpg"))
        cv2.imwrite(path, frame)
    else:
        with open(os.path.join(dir, "%s.%s" % (prefix, "txt")), mode='a'):
            pass

shutdown_handler = ShutdownHandler()

parser = argparse.ArgumentParser(description='Detect and count vehicles')
parser.add_argument('-c', '--config', help='path to config file', default='config-live.yaml')
parser.add_argument('stream', help='path to a file, RTSP stream, etc.')
args = parser.parse_args()

config = parseConfig(args.config)

model = YOLO(config['model'])
classes_to_count = config['classes_to_count']

counter = object_counter.ObjectCounter()

counter.set_args(
    view_img=True,
    reg_pts=config['region_points'],
    classes_names=model.names,
    draw_tracks=True,
    line_thickness=2,
    track_thickness=2,
    region_thickness=2
)

cap = cv2.VideoCapture(args.stream)
if config['drop_frames']:
    cap = FrameDropDecorator(cap, shutdown_handler)

assert cap.isOpened(), "Error reading video file"

count = 0

while not shutdown_handler.stopped():
    success, im0 = cap.read()
    if not success:
        exit(0)

    im0 = crop(im0, config['crop'])

    tracks = model.track(im0, persist=True, show=False, classes=classes_to_count, conf=config['confidence_threshold'])
    im0 = counter.start_counting(im0, tracks)

    if len(counter.count_ids) > count:
        store_hit(im0, config)

    count = len(counter.count_ids)
    print(count)
