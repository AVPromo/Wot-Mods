"""Read code objects without importing/executing the compiled module (Python 2.7)."""
from __future__ import print_function
import json
import marshal
import re
import sys
import types

patterns = [(name, re.compile(value, re.I)) for name, value in json.load(open(sys.argv[1]))]
data = open(sys.argv[2], 'rb').read()
if data[:4] != b'\x03\xf3\r\n':
    raise SystemExit('Wrong bytecode magic')
found = set()


def walk(value):
    if isinstance(value, types.CodeType):
        walk(value.co_filename)
        for item in value.co_consts:
            walk(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            walk(item)
    elif isinstance(value, basestring):
        if not isinstance(value, unicode):
            value = value.decode('utf-8', 'replace')
        for name, pattern in patterns:
            if pattern.search(value):
                found.add(name)


walk(marshal.loads(data[8:]))
print(json.dumps(sorted(found)))
