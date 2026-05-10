#!/usr/bin/python3

import argparse
import subprocess
import sys
import time

import span_panel

CHECK_INTERVAL_SEC = 10
MIN_CHECK_INTERVAL = 1
MIN_POWER = 0.1
MAX_POWER = 3000.0
MIN_MIN_POWER = 0.001
CIRCUIT_NAME='Kitchen / Oven'
NOTIFIER_PROGRAM='alert'
# An annoying / loud notification.  I use this script:
# (zenity --info --text="$*" --timeout=600; echo quit) | while ! read -t 1; do espeak -v 'en-us' "$*"; done

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('--show-progress', type=bool, default=False,
                   action=argparse.BooleanOptionalAction,
                   help='Show polling activity (default False).')
    p.add_argument('--check-interval', type=int, 
                   default=CHECK_INTERVAL_SEC,
                   help=f'Polling interval, in seconds (default {CHECK_INTERVAL_SEC}).')
    p.add_argument('--min-power', type=float, default=MIN_POWER,
                   help=f'Attribute value below which the circuit notification should fire (default {MIN_POWER}).')
    p.add_argument('--max-power', type=float, default=MAX_POWER,
                   help=f'Attribute value above which the circuit notification should fire (default {MAX_POWER}).')
    p.add_argument('--id', type=str, default='',
                   help='Id of the circuit to monitor.')
    p.add_argument('--circuit', type=str, default='',
                   help='Name of the circuit to monitor.  If --id is specified, this is ignored.')
    p.add_argument('--notifier', type=str, default=NOTIFIER_PROGRAM,
                   help=f'Name of notification / alert program (default {NOTIFIER_PROGRAM}).')
    p.add_argument('--message', type=str, default=None,
                   help='Argument for notification program (default "Check the [CIRCUIT] circuit").')
    p.add_argument('--attribute', type=str, default='instantPowerW',
                   help='Specify the SPAN panel circuit attribute to monitor (default "instantPowerW").')
    p.add_argument('--abs', type=bool, action=argparse.BooleanOptionalAction,
                   default=True,
                   help='Use the absolute value for min/max thresholding (default True).')
    p.add_argument('--duration', type=int, default=1,
                   help='Number of seconds value must exceed the threshold before notification is generated (avoid transients, default 1).')
    p.add_argument('--once', type=bool, action=argparse.BooleanOptionalAction,
                   default=False,
                   help='If set to True, exit after invoking notifier; otherwise check again (default False).')
    p.add_argument('--verbose', '-v', action='count', default=0,
                   help='Increment the verbosity level of debug output.')

    options = p.parse_args(argv[1:])

    if options.check_interval < MIN_CHECK_INTERVAL:
        sys.stderr.write(f'{argv[0]}: check interval {options.check_interval} must be greater than {MIN_CHECK_INTERVAL}\n')
        return 1
    if options.min_power < MIN_MIN_POWER:
        sys.stderr.write(f'{argv[0]}: over min power level {options.min_power} too low or negative; it should be at least {MIN_MIN_POWER}.\n')
        return 1
    if options.check_interval < span_panel.span_curl_max_age():
        new_cache_max_age = options.check_interval - 0.5
        if options.verbose > 1:
            sys.stderr.write(f'setting max cache age to {new_cache_max_age}\n')
        span_panel.set_span_curl_cache_max_age(new_cache_max_age)

    if options.id == '':
        options.id = None
    if options.circuit == '':
        options.circuit = None
    if options.id is None and options.circuit is None:
        options.circuit = CIRCUIT_NAME

    dots = 0
    exceed_duration = 0
    while True:
        v = span_panel.circuit_attribute_value(options.attribute, id=options.id, name=options.circuit)
        if options.verbose > 0:
            sys.stderr.write(f'v={v}\n')
        if v is None:
            sys.stderr.write(f'circuit id="{id}", name="{name}" does not exist/match\n')
            sys.exit(1)
        if options.abs:
            v = abs(v)

        if v < options.min_power or options.max_power < v:
            exceed_duration += options.check_interval
            if options.verbose > 1:
                sys.stderr.write(f'exceed_duration = {exceed_duration}\n')
            if exceed_duration >= options.duration:
                message = options.message
                if message is None:
                    if options.id is not None:
                        message = f'Check the circuit'
                    else:
                        message = f'Check the {options.circuit} circuit'
                subprocess.run([options.notifier, message])
                if options.once:
                    return 0
                exceed_duration = 0
        else:
            exceed_duration = 0
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
