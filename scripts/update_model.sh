#!/bin/bash

source=/home/egge/gdrive//dev/garbage_bin/frozen_inference_graph.pb
dest=flask/ssd/TRT_ssd_mobilenet_v1_garbage_bin.bin
if [ $source -nt $dest ]
then
  cp -pv $source /home/egge/garbage_bin/fine_tuned_model/frozen_inference_graph.pb 
  python3 ../tensorrt_demos/ssd/build_engine.py ssd_mobilenet_v1_garbage_bin
  cp -pv ../tensorrt_demos/ssd/TRT_ssd_mobilenet_v1_garbage_bin.bin $dest
fi
