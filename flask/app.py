import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, g
from werkzeug import secure_filename
import os
import six.moves.urllib as urllib
import sys
from flask import jsonify

from utils.detect import detectit,detectframe

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({"garbage_bin":0.8856315016746521,"honda_civic":0.8385475873947144,"tool_bucket":0.9996994137763977})

@app.route('/detect', methods=['POST'])
def detect():
    return jsonify(detectit(request))

@app.route('/frame', methods=['GET'])
def frame():
    return jsonify(detectframe(request))

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0',port=5000)
