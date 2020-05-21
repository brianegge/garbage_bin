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
