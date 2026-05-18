#!/usr/bin/python3

# Find circuit by name and print the returned json data.

import argparse
import json
import sys
import time

import span_panel

class JsonFinderError(Exception):
    pass

class JsonFinder:
    def __init__(self, d, kk):
        self._dd = {}
        for k, info in d.items():
            if kk not in info:
                raise JsonFinderError(f'key {kk} not found')
            if info[kk] in self._dd:
                raise JsonFinderError(f'multiple circuits has key {info[kk]}')
            self._dd[info[kk]] = info

    def find(self, k):
        return self._dd[k]


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('--all', '-a', type=bool, default=False,
                   action=argparse.BooleanOptionalAction,
                   help='Print circuit information for all circuits.')
    p.add_argument('--id', '-i', nargs='*', default=[],
                   help='Print circuit information for list of circuit identified by their IDs.')
    p.add_argument('--name', '-n', nargs='*', default=[],
                   help='Print circuit information for list of circuit identified by their (user assigned) names.')
    p.add_argument('--key', '-k', type=str, default='',
                   help='If specified, instead of printing JSON for the selected circuit(s), print only the value corresponding to the given key.  If multiple circuits are selected, the values are printed on a single line, separated by SEPARATOR.  The (unlabeled) values are output in the following order:  id circuits first, then named circuits; if --all was used, then the order is sorted by key (ID).')
    p.add_argument('--separator', '-s', type=str, default=' ',
                   help='When --key is used and multiple circuits are selected, the value associated with the key are printed on a single line, separated by this character.') 
    p.add_argument('--live', type=int, default=0,
                   help='If non-zero, poll the panel every LIVE seconds in an infinite loop.  This is used in conjunction with live_plotter or similar programs.')
    options = p.parse_args(argv[1:])

    if not options.all and len(options.id) == 0 and len(options.name) == 0:
        sys.stderr.write(f'{argv[0]}: No circuits specified.\n')
        return 1

    while True:
        d = span_panel.get_circuits()
        if d is None:
            sys.stderr.write(f'{argv[0]}: Could not get circuit information.')
            return 1
        out = {}
        kwargs = {'indent': 4, 'ensure_ascii': False}
        if options.all:
            if options.key == '':
                out = d
            else:
                for k, v in d.items():
                    out[k] = v[options.key]
            kwargs['sort_keys'] = True
        else:
            # Since Python 3.7, dict insertion order is preserved.
            if len(options.id) != 0:
                try:
                    f = JsonFinder(d, 'id')
                    for id in options.id:
                        if options.key == '':
                            out[id] = f.find(id)
                        else:
                            out[id] = f.find(id)[options.key]
                except (JsonFinderError, KeyError) as e:
                    sys.stderr.write(f'{argv[0]}: {e}')
                    return 1
            if len(options.name) != 0:
                try:
                    f = JsonFinder(d, 'name')
                    for n in options.name:
                        if options.key == '':
                            out[n] = f.find(n)
                        else:
                            out[n] = f.find(n)[options.key]
                except (JsonFinderError, KeyError) as e:
                    sys.stderr.write(f'{argv[0]}: {e}')
                    return 1
    
        if options.key == '':
            print(f'{json.dumps(out, **kwargs)}')
        else:
            print(f'{options.separator.join(str(v) for v in out.values())}')
        if options.live == 0:
            break
        sys.stdout.flush()
        time.sleep(options.live)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
