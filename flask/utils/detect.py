import os
from datetime import date,datetime
import json
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
# from utils.ssd import TrtSSD
#import pycuda.driver as cuda
import imageio
import logging
import requests
from io import BytesIO
from pprint import pprint

MODEL='ssd_mobilenet_v1_garbage_bin'
cls_dict = get_cls_dict()
INPUT_HW = (300, 300)

def sanitize(j):
    o={}
    for k,v in j.items():
        o[k.replace(' ','_')] = v
    return o

def detect(model,request):
    #read image file string data
    img = cv2.imdecode(numpy.fromstring(request, numpy.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        return ['Error reading image']
    boxes, confs, clss = model.detect(img)
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
        o[cls_dict[k]] = v.item()
    return sanitize(o)

#def detectit(request):
#    #read image file string data
#    img = cv2.imdecode(numpy.fromstring(request.files['file'].read(), numpy.uint8), cv2.IMREAD_UNCHANGED)
#    print('getting cuda context')
#    cuda.init()
#    device = cuda.Device(0) # enter your gpu id here
#    ctx = device.make_context()
#    print('loading model')
#    ssd = TrtSSD(MODEL, INPUT_HW)
#    print('detecting')
#    boxes, confs, clss = ssd.detect(img)
#    ctx.pop()
#    maxes={}
#    for i,_ in enumerate(confs):
#        conf = confs[i]
#        cls = clss[i]
#        if not cls in maxes:
#            maxes[cls] = conf
#        if conf > maxes[cls]:
#            maxes[cls] = conf
#    o={}
#    for k,v in maxes.items():
#        o[cls_dict[k]] = v
#    return sanitize(o)

def save(image, predictions):
    good_predictions = dict(filter(lambda elem: elem[1] > 0.8, predictions.items()))
    detected_objects = list(good_predictions.keys())
    detected_objects = list(filter(lambda x: x != 'something', detected_objects))
    pathname = os.path.join('/mnt/elements/capture/', date.today().strftime("%Y%m%d"))
    os.makedirs(pathname, exist_ok=True)
    basename = os.path.join(pathname, datetime.now().strftime("%H%M%S") + "-" + "garage_check" + "-" + "_".join(detected_objects))
    logging.info('Saving %s',  basename)
    #pimg = Image.fromarray(image)
    image.save(basename + '.jpg')
    with open(basename + '.txt', 'w') as file:
        file.write(json.dumps(predictions))
    
def detectframe(model):
    #read image file string data
    url = "http://garage:8085/?action=snapshot"
    #img = imageio.imread(url)
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    #img = cv2.imdecode(numpy.fromstring(request, numpy.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        return ['Error reading image']
    output = model.detect(img)
    boxes = output['detection_boxes']
    confs = output['detection_scores']
    clss = output['detection_classes']
    maxes={}
    something = numpy.float32(-1.0)
    for i,_ in enumerate(confs):
        conf = confs[i]
        cls = clss[i]
        if not cls in maxes:
            maxes[cls] = conf
        if conf > maxes[cls]:
            maxes[cls] = conf
        if cls_dict[cls] != 'honda civic':
            something = max(something, conf)
    o={}
    for k,v in maxes.items():
        if v.item() > 0.4:
            o[cls_dict[k]] = v.item()
    o['something'] = something.item()
    o = sanitize(o)
    save(img, o)
    return o
