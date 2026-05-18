#!/usr/bin/python3

import argparse
from datetime import datetime
from enum import Enum
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

class MonitorMode(Enum):
    once = 'once'
    transitions = 'transitions'
    continuous = 'continuous'

    def __str__(self):
        return self.value

class Excursion(Enum):
    none = 0  # initial state or in-between low and high
    low = 1
    high = 2

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('--show-progress', type=bool, default=False,
                   action=argparse.BooleanOptionalAction,
                   help='Show polling activity (default False).')

    p.add_argument('--check-interval', type=int, 
                   default=CHECK_INTERVAL_SEC,
                   help=f'Polling interval, in seconds (default {CHECK_INTERVAL_SEC}).')
    p.add_argument('--duration', type=int, default=1,
                   help='Number of seconds value must exceed the threshold before notification is generated (avoid transients, default 1).')
    p.add_argument('--mode', type=MonitorMode,
                   choices=[MonitorMode.once, MonitorMode.transitions, MonitorMode.continuous],
                   default=MonitorMode.once,
                   help='Choose monitoring mode: once means exiting after notifying once; continuous means notifying whenever the value is in a reportable zone; transitions means notifying upon entry to a reportable zone.')

    p.add_argument('--id', type=str, default='',
                   help='Id of the circuit to monitor.')
    p.add_argument('--name', type=str, default='',
                   help='Name of the circuit to monitor.  If --id is specified, this is ignored.')

    p.add_argument('--attribute', type=str, default='instantPowerW',
                   help='Specify the SPAN panel circuit attribute to monitor (default "instantPowerW").')
    p.add_argument('--abs', type=bool, action=argparse.BooleanOptionalAction,
                   default=True,
                   help='Use the absolute value for min/max thresholding (default True).')

    p.add_argument('--lower-threshold', '-l', type=float, default=MIN_POWER,
                   help=f'Attribute value below which the circuit notification should fire (default {MIN_POWER}).')
    p.add_argument('--upper-threshold', '-u', type=float, default=MAX_POWER,
                   help=f'Attribute value above which the circuit notification should fire (default {MAX_POWER}).')

    p.add_argument('--notifier', type=str, default=NOTIFIER_PROGRAM,
                   help=f'Name of notification / alert program (default {NOTIFIER_PROGRAM}).')
    p.add_argument('--message', type=str, default=None,
                   help='Argument for notification program (default "Check the [CIRCUIT] circuit").')

    p.add_argument('--verbose', '-v', action='count', default=0,
                   help='Increment the verbosity level of debug output.')

    options = p.parse_args(argv[1:])

    if options.check_interval < MIN_CHECK_INTERVAL:
        sys.stderr.write(f'{argv[0]}: check interval {options.check_interval} must be greater than {MIN_CHECK_INTERVAL}\n')
        return 1
    if options.lower_threshold < MIN_MIN_POWER:
        sys.stderr.write(f'{argv[0]}: over min power level {options.lower_threshold} too low or negative; it should be at least {MIN_MIN_POWER}.\n')
        return 1

    if options.id == '':
        options.id = None
    if options.name == '':
        options.name = None
    if options.id is None and options.name is None:
        options.name = CIRCUIT_NAME

    dots = 0
    exceed_duration = 0

    state = Excursion.none
    prev = Excursion.none

    panels = span_panel.AuthInfo()
    panel = panels.panel()  # default panel

    while True:
        try:
            v = panel.attribute_value(options.attribute, id=options.id, name=options.name)
            if options.verbose > 1:
                sys.stderr.write(f'v={v}\n')
        except (span_panel.SpanError, KeyError) as e:
            sys.stderr.write(f'{argv[0]}: circuit id="{options.id}", name="{options.name}" error {e}\n')
            sys.stderr.write(f'{argv[0]}: assuming transient error\n') 
            # sys.exit(1)
            continue
        if options.abs:
            v = abs(v)

        cur = Excursion.none
        if v < options.lower_threshold:
            cur = Excursion.low
        elif options.upper_threshold < v:
            cur = Excursion.high

        if cur != prev:
            exceed_duration = 0
        else:
            exceed_duration += options.check_interval
            if options.verbose > 2:
                sys.stderr.write(f'{argv[0]}: exceed_duration = {exceed_duration}\n')
            if exceed_duration >= options.duration:
                # this is a "real" state
                if options.verbose > 1:
                    sys.stderr.write(f'{argv[0]}: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: {cur}\n')
                # but if it is not moving from high to low or vice versa (e.g.,
                # low to none), should we ignore it?
                if cur != Excursion.none and (options.mode == MonitorMode.once or options.mode == MonitorMode.continuous or (options.mode == MonitorMode.transitions and cur != state)):
                    message = options.message
                    if message is None:
                        if options.id is not None:
                            message = f'Check the circuit'
                        else:
                            message = f'Check the {options.name} circuit'
                    if options.verbose > 0:
                        sys.stderr.write(f'{argv[0]}: state: {cur}, message: {message}\n')
                    subprocess.run([options.notifier, message])
                    if options.mode == MonitorMode.once:
                        return 0
                    # update state only if not Excursion.none, we have
                    # notified the state transition, etc
                    state = cur
        prev = cur
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
