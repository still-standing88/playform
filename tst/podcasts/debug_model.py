import os
import pickle
from feed_widget import EntryTableModel, FeedWidget
from PySide6.QtCore import QModelIndex

base = os.path.join(os.path.dirname(__file__), 'cache')
path = None
for name in os.listdir(base):
    if name.endswith('.pickle'):
        path = os.path.join(base, name)
        break
if not path:
    raise SystemExit('no cache file')

with open(path, 'rb') as fh:
    data = pickle.load(fh)

entries = list(getattr(data, 'entries', []))
print('entries count', len(entries))

model = EntryTableModel()
model.set_entries(entries)
print('columns', model._columns)
if entries:
    entry = entries[0]
    print('entry type', type(entry))
    print('isinstance dict', isinstance(entry, dict))
    print('has __dict__', hasattr(entry, '__dict__'))
    idx = model.index(0, 0)
    print('first value', model.data(idx))
