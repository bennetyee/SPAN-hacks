#!/usr/bin/python3

import argparse
import subprocess
import sys
import time

import span_panel

CHECK_INTERVAL_SEC = 2
MIN_CHECK_INTERVAL = 1
MIN_POWER = 0.1
MIN_MIN_POWER = 0.001
CIRCUIT_NAME='Kitchen / Oven'

def circuit_has_power(name, min_power):
    return abs(span_panel.circuit_power_by_name(name)) > MIN_POWER

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('--show-progress', type=bool, default=False,
                   action=argparse.BooleanOptionalAction,
                   help='print dots and commas to show progress')
    p.add_argument('--check-interval', type=int, 
                   default=CHECK_INTERVAL_SEC,
                   help='number of seconds between polling')
    p.add_argument('--min-power', type=float, default=MIN_POWER,
                   help='power level below which the circuit is considered to be off')
    p.add_argument('--circuit', type=str, default=CIRCUIT_NAME,
                   help='name of the circuit to monitor')

    options = p.parse_args(argv[1:])

    if options.check_interval < MIN_CHECK_INTERVAL:
        sys.stderr.write(f'{argv[0]}: check interval {options.check_interval} must be greater than {MIN_CHECK_INTERVAL}\n')
        return 1
    if options.min_power < MIN_MIN_POWER:
        sys.stderr.write(f'{argv[0]}: over min power level {options.min_power} too low or negative; it should be at least {MIN_MIN_POWER}.\n')
        return 1
    if options.check_interval >= span_panel.span_curl_max_age():
        span_panel.set_span_curl_cache_max_age(options.check_interval - 0.1)

    dots = 0
    while True:
        if not circuit_has_power(options.circuit, options.min_power):
            subprocess.run(['alert', 'check', 'breaker', 'for', options.circuit])
        time.sleep(CHECK_INTERVAL_SEC)
        if options.show_progress:
            dots += 1
            if dots % 100 == 0:
                sys.stdout.write('|')
                dots = 0
            elif dots % 10 == 0:
                sys.stdout.write(',')
            else:
                sys.stdout.write('.')
            sys.stdout.flush()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
