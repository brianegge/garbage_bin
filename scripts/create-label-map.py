#!/usr/bin/python3

import fileinput

# stdin garbage_bin/images/labels.txt
# stdout label_map.pbtxt

"""
item {
    id: 1
    name: 'garbage bin'
}
"""
counter=1
for label in fileinput.input():
    print("""item {{
    id: {}
    name: '{}'
}}
""".format(counter,label.rstrip()))
    counter += 1
