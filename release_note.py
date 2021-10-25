import sys
from pathlib import Path

import orjson

if __name__ == '__main__':
    obj1 = orjson.loads(Path('event.json').read_bytes())
    print(f'json file: {len(obj1)} keys')
    arg = sys.argv[1]
    if arg:
        obj2 = orjson.loads(arg)
        print(f'arg json: {len(obj2)} keys')
    else:
        print(f'No arg found')
