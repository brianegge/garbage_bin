import re

def get_cls_dict():
    with open('../annotations/label_map.pbtxt') as fp:
        label_map={}
        for line in map(str.rstrip, fp):
            m = re.match(r'\s+id: ([0-9]+)', line)
            if m:
                i = int(m[1])
            m = re.match('\s+name: \'(.*)\'', line)
            if m:
                name = m[1]
                label_map[i] = name
    return label_map
