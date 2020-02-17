#!/bin/bash -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd /home/egge/gdrive/dev/garbage_bin
echo "Running prepare in $(pwd)"
${SCRIPT_DIR}/create-label-map.py images/labels.txt > annotations/label_map.pbtxt
python3 ${SCRIPT_DIR}/xml_to_csv.py -i images -o annotations/labels.csv
${SCRIPT_DIR}/split_labels.py
python3 ${SCRIPT_DIR}/generate_tfrecord.py --csv_input=annotations/train_labels.csv --label_map=annotations/label_map.pbtxt --img_path=images --output_path=annotations/train.record
python3 ${SCRIPT_DIR}/generate_tfrecord.py --csv_input=annotations/test_labels.csv --label_map=annotations/label_map.pbtxt --img_path=images --output_path=annotations/test.record
