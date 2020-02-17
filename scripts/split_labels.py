#!/usr/bin/python3

import sys
import numpy as np
import pandas as pd
np.random.seed(1)

full_labels = pd.read_csv('annotations/labels.csv')
grouped = full_labels.groupby('filename')
gb = full_labels.groupby('filename')
grouped_list = [gb.get_group(x) for x in gb.groups]


train_index = np.random.choice(len(grouped_list), size=int(len(grouped_list) * 0.8), replace=False)
test_index = np.setdiff1d(list(range(len(grouped_list))), train_index)

train = pd.concat([grouped_list[i] for i in train_index])
test = pd.concat([grouped_list[i] for i in test_index])

print ('train samples={}, test samples={}'.format(len(train), len(test)))

train.to_csv('annotations/train_labels.csv', index=None)
test.to_csv('annotations/test_labels.csv', index=None)
