#!/usr/bin/python3

# Find circuit by name and print the returned json data.

import json
import sys

import span_panel

def main(argv):
    had_errors = 0
    if len(argv) < 2:
        # dump all circuits
        info = span_panel.get_circuits()
        if info is None:
            had_errors = 1
        else:
            print(json.dumps(info, indent=4, sort_keys=True, ensure_ascii=False))
    else:
        for name in argv[1:]:
            info = span_panel.get_circuit_info_by_name(name)
            if info is None:
                print(f'{name}: NOT FOUND')
                had_errors = 1
            else:
                print(f'{name}: {json.dumps(info, indent=4, sort_keys=True, ensure_ascii=False)}')
    return had_errors

if __name__ == '__main__':
    sys.exit(main(sys.argv))
