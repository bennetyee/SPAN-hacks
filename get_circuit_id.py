#!/usr/bin/python3

# Find circuit by name and print their ID.

import sys

import span_panel

def main(argv):
    had_errors = 0
    for name in argv[1:]:
        v = span_panel.circuit_attribute_value('id', name=name)
        if v is None:
            print(f'{name}: NOT FOUND')
            had_errors = 1
        else:
            print(f'{name}: {v}')
    return had_errors

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write(f'{sys.argv[0]}: no circuit name provided\n')
        sys.exit(1)
    sys.exit(main(sys.argv))
