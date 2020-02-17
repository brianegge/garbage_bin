
import numpy
import cv2
import tensorflow as tf
import subprocess
from collections import defaultdict
from io import StringIO
from PIL import Image
from utils.ssd_labels import get_cls_dict
from flask import g
# import pycuda.autoinit  # This is needed for initializing CUDA driver
from utils.ssd import TrtSSD
import pycuda.driver as cuda

MODEL='ssd_mobilenet_v1_garbage_bin'
cls_dict = get_cls_dict()
INPUT_HW = (300, 300)

def sanitize(j):
    o={}
    for k,v in j.items():
        o[k.replace(' ','_')] = v
    return o

def detectit(request):
    #read image file string data
    img = cv2.imdecode(numpy.fromstring(request.files['file'].read(), numpy.uint8), cv2.IMREAD_UNCHANGED)
    print('getting cuda context')
    cuda.init()
    device = cuda.Device(0) # enter your gpu id here
    ctx = device.make_context()
    print('loading model')
    ssd = TrtSSD(MODEL, INPUT_HW)
    print('detecting')
    boxes, confs, clss = ssd.detect(img)
    ctx.pop()
    maxes={}
    for i,_ in enumerate(confs):
        conf = confs[i]
        cls = clss[i]
        if not cls in maxes:
            maxes[cls] = conf
        if conf > maxes[cls]:
            maxes[cls] = conf
    o={}
    for k,v in maxes.items():
        o[cls_dict[k]] = v
    return sanitize(o)

def detectframe(request):
    print('capturing frame')
    subprocess.call('/home/egge/garbage_bin/scripts/capture.sh')
    print('getting cuda context')
    cuda.init()
    device = cuda.Device(0) # enter your gpu id here
    ctx = device.make_context()
    print('loading model')
    ssd = TrtSSD(MODEL, INPUT_HW)
    #read image file string data
    _, img = cv2.VideoCapture('/tmp/ramdisk/frame.jpg').read()
    print('detecting')
    boxes, confs, clss = ssd.detect(img)
    ctx.pop()
    maxes={}
    for i,_ in enumerate(confs):
        conf = confs[i]
        cls = clss[i]
        if not cls in maxes:
            maxes[cls] = conf
        if conf > maxes[cls]:
            maxes[cls] = conf
    o={}
    for k,v in maxes.items():
        o[cls_dict[k]] = v
    return sanitize(o)
