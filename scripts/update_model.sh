#!/bin/bash

set -o errexit

source=/home/egge/gdrive//dev/garbage_bin/frozen_inference_graph.pb
dest=flask/ssd/TRT_ssd_mobilenet_v1_garbage_bin.bin
cd /home/egge/garbage_bin

if [ ! -e $source ]
then
  echo "Maounting Google Drive"
  google-drive-ocamlfuse /home/egge/gdrive
fi
if [ $source -nt $dest ]
then
  wc -c $source # force gdrive to fetch
  cp -pv $source /home/egge/garbage_bin/fine_tuned_model/frozen_inference_graph.pb 
  # must patch graphsurgeon https://github.com/AastaNV/TRT_object_detection
  #/usr/bin/python3 ~/tensorrt_demos/ssd/build_engine.py ssd_mobilenet_v1_garbage_bin
  #cp -pv ~/tensorrt_demos/ssd/TRT_ssd_mobilenet_v1_garbage_bin.bin $dest
  echo "Restarting service - sudo required"
  echo sudo systemctl restart garbage_bin_detector
else
  echo "Model is up to date - nothing to do"
fi
