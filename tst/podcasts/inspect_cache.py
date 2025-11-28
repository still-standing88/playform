import os
import glob
import pickle
from pprint import pprint

base = os.path.join(os.path.dirname(__file__), 'cache')
files = glob.glob(os.path.join(base, '*.pickle'))
print('cache files:', len(files))
if not files:
    raise SystemExit(0)

for path in files[:1]:
    print('Inspecting', os.path.basename(path))
    with open(path, 'rb') as fh:
        data = pickle.load(fh)
    entries = getattr(data, 'entries', [])
    print('entry count:', len(entries))
    if not entries:
        continue
    entry = entries[0]
    print('entry type:', type(entry))
    if hasattr(entry, 'keys'):
        keys = list(entry.keys())
        print('keys sample:', keys[:10])
    print('attributes:', [k for k in dir(entry) if not k.startswith('_')][:10])
    print('title via attr:', getattr(entry, 'title', None))
    print('title via dict:', entry.get('title'))
