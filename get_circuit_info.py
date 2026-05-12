#!/usr/bin/python3

# Find circuit by name and print the returned json data.

import argparse
import json
import sys

import span_panel

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('--id', '-i', nargs='*',
                   help='list of circuit ids')
    p.add_argument('--name', '-n', nargs='*',
                   help='list of circuit names')
    options = p.parse_args(argv[1:])

    had_errors = 0
    d = span_panel.get_circuits()
    if d is None:
        sys.stderr.write(f'Could not get circuit information.')
        return 1
    out = {}
    if options.id is not None:
        for id in options.id:
            found = False
            for k, info in d.items():
                if 'id' in info and info['id'] == id:
                    out[k] = info
                    found = True
                    break
            if not found:
                sys.stderr.write(f'Could not get circuit information for id {id}\n')
                return 1
    if options.name is not None:
        for n in options.name:
            found = False
            for k, info in d.items():
                if 'name' in info and info['name'] == n:
                    out[k] = info
                    found = True
                    break
            if not found:
                sys.stderr.write(f'Could not get circuit information for name {n}\n')
                return 1

    if len(out) == 0:
        # dump all circuits
        out = d
    print(f'{json.dumps(out, indent=4, sort_keys=True, ensure_ascii=False)}')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
