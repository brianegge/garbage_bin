#!/bin/bash

set -o errexit

source=/home/egge/gdrive//dev/garbage_bin/frozen_inference_graph.pb
labels=/home/egge/gdrive//dev/garbage_bin/my-garage_label_map.pbtxt
dest=flask/ssd/TRT_ssd_mobilenet_v1_garbage_bin.bin
cd $(cd $(dirname $0)/..; pwd)
pwd

if [[ ! -e $source ]] && which google-drive-ocamlfuse
then
  echo "Maounting Google Drive"
  google-drive-ocamlfuse /home/egge/gdrive
fi

if [ -e $source ]
then
  if [ $source -nt $dest ]
  then
    wc -c $source # force gdrive to fetch
    cp -pv $source $labels /home/egge/garbage_bin/fine_tuned_model/
    # must patch graphsurgeon https://github.com/AastaNV/TRT_object_detection
    #/usr/bin/python3 ~/tensorrt_demos/ssd/build_engine.py ssd_mobilenet_v1_garbage_bin
    #cp -pv ~/tensorrt_demos/ssd/TRT_ssd_mobilenet_v1_garbage_bin.bin $dest
    echo "Restarting service - sudo required"
    echo sudo systemctl restart garbage_bin_detector
  else
    echo "Model is up to date - nothing to do"
  fi
else
  rclone copy --progress gdrive:/dev/garbage_bin/frozen_inference_graph.pb ~/garbage_bin/fine_tuned_model/
  rclone copy --progress gdrive:/dev/garbage_bin/my-garage_label_map.pbtxt ~/garbage_bin/fine_tuned_model/
fi

echo sudo systemctl  restart garbage_bin_detector
echo time curl http://localhost:5000/
