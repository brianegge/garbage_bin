#!/bin/sh

ffmpeg -y -rtsp_transport tcp -i rtsp://garage.local:8555/unicast  -vf fps=1 -vframes 1 /tmp/ramdisk/frame.jpg
