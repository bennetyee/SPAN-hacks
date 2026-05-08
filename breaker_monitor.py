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
NOTIFIER_PROGRAM='alert'
# An annoying / loud notification.  I use this script:
# (zenity --info --text="$*" --timeout=600; echo quit) | while ! read -t 1; do espeak -v 'en-us' "$*"; done

def circuit_has_power(id, name, min_power):
    if id != '':
        power = span_panel.circuit_power_by_id(id)
    else:
        power = span_panel.circuit_power_by_name(name)
    if power is None:
        sys.stderr.write(f'circuit id="{id}", name="{name}" does not exist/match\n')
        sys.exit(1)
    return abs(power) > min_power

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('--show-progress', type=bool, default=False,
                   action=argparse.BooleanOptionalAction,
                   help='Show polling activity.')
    p.add_argument('--check-interval', type=int, 
                   default=CHECK_INTERVAL_SEC,
                   help='Polling interval, in seconds')
    p.add_argument('--min-power', type=float, default=MIN_POWER,
                   help='Power level below which the circuit is considered to be off')
    p.add_argument('--circuit', type=str, default=CIRCUIT_NAME,
                   help='Name of the circuit to monitor.  If --id is specified, this is ignored.')
    p.add_argument('--id', type=str, default='',
                   help='Id of the circuit to monitor')
    p.add_argument('--notifier', type=str, default=NOTIFIER_PROGRAM,
                   help='Name of notification / alert program')
    p.add_argument('--message', type=str, default=None,
                   help='Argument for notification program')

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
        if not circuit_has_power(options.id, options.circuit, options.min_power):
            message = options.message
            if message is None:
                if options.id != '':
                    message = f'Check the circuit breaker'
                else:
                    message = f'Check the {options.circuit} circuit breaker'
            subprocess.run([options.notifier, message])
        time.sleep(options.check_interval)
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
