import re
from pprint import pprint

def get_cls_dict():
    with open('../annotations/label_map.pbtxt') as fp:
        label_map={}
        name=None
        i=None
        for line in map(str.rstrip, fp):
            m = re.match('\s+id: ([0-9]+)', line)
            if m:
                i = int(m[1])
            m = re.match('\s+name: [\'\"](.*)[\'\"]', line)
            if m:
                name = m[1]
            if i is not None and name is not None:
                label_map[i] = name
                name = i = None
    print("Loaded label map:")
    pprint(label_map)
    return label_map
