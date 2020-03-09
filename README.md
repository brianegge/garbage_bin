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
