#!/usr/bin/python3

# Find circuit by name and print the returned json data.

import argparse
import json
import sys

import span_panel

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('--all', '-a', type=bool, default=False,
                   action=argparse.BooleanOptionalAction,
                   help='Print circuit information for all circuits.')
    p.add_argument('--id', '-i', nargs='*', default=[],
                   help='Print circuit information for list of circuit identified by their IDs.')
    p.add_argument('--name', '-n', nargs='*', default=[],
                   help='Print circuit information for list of circuit identified by their (user assigned) names.')
    options = p.parse_args(argv[1:])

    if not options.all and len(options.id) == 0 and len(options.name) == 0:
        sys.stderr.write(f'{argv[0]}: No circuits specified.\n')
        return 1

    d = span_panel.get_circuits()
    if d is None:
        sys.stderr.write(f'{argv[0]}: Could not get circuit information.')
        return 1
    out = {}
    if options.all:
        out = d
    else:
        for id in options.id:
            found = False
            for k, info in d.items():
                if 'id' in info and info['id'] == id:
                    out[k] = info
                    found = True
                    break
            if not found:
                sys.stderr.write(f'{argv[0]}: Could not get circuit information for id {id}\n')
                return 1
        for n in options.name:
            found = False
            for k, info in d.items():
                if 'name' in info and info['name'] == n:
                    out[k] = info
                    found = True
                    break
            if not found:
                sys.stderr.write(f'{argv[0]}: Could not get circuit information for name {n}\n')
                return 1

    print(f'{json.dumps(out, indent=4, sort_keys=True, ensure_ascii=False)}')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
