To label more images

*MacOS install*
```
git clone https://github.com/tzutalin/labelImg.git
brew install qt  # will install qt-5.x.x
brew install libxml2
make qt5py3
python3 labelImg.py
python3 labelImg.py [IMAGE_PATH] [PRE-DEFINED CLASS FILE]
python3 ~/dev/labelImg/labelImg.py . labels.txt
```

```
DISPLAY=:0 /home/egge/labelImg/labelImg.py images/ images/labels.txt
```

Install service
```
$ cat /etc/systemd/system/garbage_bin_detector.service
[Unit]
Description=Image processor to find the garbage bin
After=network.target
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=1
User=egge
WorkingDirectory=/home/egge/garbage_bin/flask
ExecStart=/home/egge/garbage_bin/flask/simple.py

[Install]
WantedBy=multi-user.target
```

Fix /usr/lib/python3.6/dist-packages/graphsurgeon/node_manipulation.py

```
def create_node(name, op=None, trt_plugin=False, **kwargs):
    '''
    Creates a free-standing TensorFlow NodeDef with the specified properties.

    Args:
        name (str): The name of the node.
        op (str): The node's operation.

    Keyword Args:
        dtype (tensorflow.DType): TensorFlow dtype.
        shape (tuple(int)): Iterable container (usually a tuple) describing the shape of a tensor.
        inputs (list(tensorflow.NodeDef) or str): Iterable container (usually a tuple) of input nodes or input node names. Supports mixed-type lists.
        **kwargs (AttrName=Value): Any additional fields that should be present in the node. Currently supports int, float, bool, list(int), list(float), str and NumPy arrays. NumPy arrays will be inserted into the "value" attribute of the node - this can be useful for creating constant nodes equivalent to those created by tensorflow.constant.

    Returns:
        tensorflow.NodeDef
    '''
    node = tf.compat.v1.NodeDef()
    node.attr["dtype"].type = 1 # Add this line
    return update_node(node, name, op, trt_plugin, **kwargs)
```

