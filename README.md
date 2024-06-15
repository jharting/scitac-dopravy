# Sčítač dopravy

Scripts for video-based automated counting and reporting of vehicle traffic.
The [yolov8 model](https://github.com/ultralytics/ultralytics) is used for detecting and tracking vehicles based on a live video stream.
Traffic data is aggregated and a report compatible with [TP 189](https://pjpk.rsd.cz/data/USR_001_2_8_TP/TP_189_2018_final.pdf) (Czech standard for measuring road traffic intensity) can be generated.

## Installation

```sh
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Detection script configuration is by default read from the `config-live.yaml` file.
The file provides reasonable defaults for detecting vehicles in a live video stream.
The detection region should be adjusted based on the given location.

## Vehicle detection

Start the detection script by running:

```sh
python detect.py <live stream URL>
```

A preview of the augmented video stream will pop up.

![preview](./docs/example.jpg)

An empty file is created in `workdir` every time a vehicle is detected.
The file name contains a timestamp of when the detection occurred.
The files are organized in nested folders based on the date.

## Generating reports

Reports can be generated from information stored in `workdir`.

```sh
python evaluate.py

2024-02-05,08:45,09:45,113
2024-02-06,08:15,09:15,117
2024-02-07,08:45,09:45,124
2024-02-08,08:00,09:00,138
2024-02-09,08:00,09:00,126
```

By default, for each day the script identifies the peak hour (4 subsequent 15-minute blocks with highest traffic) within a given window (7:00-17:00 by default).
Alternatively, a full report which includes the traffic count for each 15-minute block can be generated:

```sh
python evaluate.py -f full

2024-02-05,08:30,08:45,14, 
2024-02-05,08:45,09:00,35, 
2024-02-05,09:00,09:15,22, 
2024-02-05,09:15,09:30,21,92
2024-02-05,09:30,09:45,35,113
2024-02-05,09:45,10:00,20,98
2024-02-05,10:00,10:15,28,104
2024-02-05,10:15,10:30,19,102
2024-02-05,10:30,10:45,27,94
2024-02-05,10:45,11:00,30,104
```

The last column contains the traffic sum for the corresponding "floating hour" i.e. sum of the given 15-minute block plus three immediatelly preceeding blocks (if available).

### Uploading reports to Google Sheets

The reports can be directly uploaded to Google Sheets:

1. Follow [py_gsheets documetation](https://erikrood.com/Posts/py_gsheets.html) to obtain a service account key.
1. Run the evaluate script

  ```sh
  python evaluate.py -d 'name of the Google Sheet' -saf 'path-to-service-account-key' -s 'sheet number'
  ```

## Running on NVIDIA Jetson Nano

1. Follow https://medium.com/@jgleeee/building-docker-images-that-require-nvidia-runtime-environment-1a23035a3a58 to configure nvidia as the default Docker runtime
1. Build the container image

   ```sh
   sudo docker build . -t traffic
   ```

1. Run the container

   ```sh
   sudo docker run -v $(pwd)/workdir:/traffic/workdir -e TZ=Europe/Prague traffic -- <stream>
   ```
