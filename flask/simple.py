#!/usr/bin/python3
"""
Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import logging
from utils.detect import detect,detectframe
#from utils.ssd import TrtSSD,TfSSD
from utils.ssd2 import TfSSD2
import sdnotify
import json
from pprint import pprint

ssd = None

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        self._set_response()
        out = json.dumps(detectframe(ssd)).encode('utf-8')
        self.wfile.write(out)

    def do_POST(self):
        form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                    'CONTENT_TYPE':self.headers['Content-Type'],
                    })
        # filename = form['file'].filename
        data = form['file'].file.read()
        #logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody size:\n%s\n",
        #        str(self.path), str(self.headers), len(data))
        img = Image.open(BytesIO(data))
        self._set_response()
        out = json.dumps(detect(ssd, img)).encode('utf-8')
        self.wfile.write(out)

def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd on port {}...\n'.format(port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    print('loading model')
    #ssd = TrtSSD('ssd_mobilenet_v1_garbage_bin', (300, 300))
    #ssd = TfSSD('frozen_inference_graph', (300, 300))
    ssd = TfSSD2('frozen_inference_graph', (300, 300))
    # warm up
    pprint(json.dumps(detectframe(ssd)).encode('utf-8'))
    #pprint(json.dumps(detectframe(ssd)).encode('utf-8'))
    n = sdnotify.SystemdNotifier()
    n.notify("READY=1")
    run(port=5000)
