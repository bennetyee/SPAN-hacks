#!/usr/bin/python

import json
import subprocess
import sys
import time

SPAN_CURL_CACHE_MAX_AGE = 5
SPAN_CURL_CACHE = None
SPAN_CURL_CACHE_TIME = None

def span_curl_max_age():
    return SPAN_CURL_CACHE_MAX_AGE

def set_span_curl_cache_max_age(seconds):
    global SPAN_CURL_CACHE_MAX_AGE
    assert seconds >= 0
    SPAN_CURL_CACHE_MAX_AGE = seconds

def span_curl(api):
    global SPAN_CURL_CACHE
    global SPAN_CURL_CACHE_TIME
    now = time.time()
    if SPAN_CURL_CACHE_TIME is None or now > SPAN_CURL_CACHE_TIME + SPAN_CURL_CACHE_MAX_AGE:
        SPAN_CURL_CACHE = subprocess.run(['span-curl', api], capture_output=True, text=True)
        SPAN_CURL_CACHE_TIME = now
    return (SPAN_CURL_CACHE.stdout, SPAN_CURL_CACHE.returncode)

def get_circuits():
    data, status = span_curl('/api/v1/circuits')
    if status == 0:
        d = json.loads(data)
        if 'circuits' not in d:
            return None
        return d['circuits']
    return None

def get_circuit_info_by_id(id):
    """Get the info json dict for a circuit.  The circuit must be
    identified by the its unique |id| (long hex string).

    """

    circ = get_circuits()
    if circ is None:
        return None
    if id not in circ.keys():
        return None
    return circ[id]

def circuit_attribute_value(attribute, id = None, name = None):
    if id is None and name is None:
        sys.stderr.write(f'Panic: circuit_attribute_value, both id and name are None\n')
        sys.exit(1)
    if id is not None and name is not None:
        sys.stderr.write(f'Panic: circuit_attribute_value, id={id} and name={name} are mutually exclusive. One should be None.\n')
        sys.exit(1)
    if id is not None:
        info = get_circuit_info_by_id(id)
    else:
        info = get_circuit_info_by_name(name)
    if info is not None and attribute in info:
        return info[attribute]
    return None

def get_circuit_info_by_name(circuit_name):
    """Get the info json dict for a circuit.  The circuit must be
    identified by the user-settable |circuit_name|, which is matched
    exactly.
    """

    circ = get_circuits()
    if circ is None:
        return None
    for id in circ.keys():
        info = circ[id]
        if 'name' in info and info['name'] == circuit_name:
            return info
    return None

def circuit_power_by_id(id):
    """Get the instantaneous power through a circuit.  The circuit
    must be named by the its uniquie |id| (long hex string).

    Since the Current Transformers (CTs) are sometimes installed
    backwards during panel installation (mine was!), the instantPowerW
    value could be negative (which do normally occur for circuits that
    might feed power back to the grid, e.g., solar), beware!  The
    caller should know whether negation or using the absolute value is
    appropriate for the circuit.
    """

    return circuit_attribute_value('instantPowerW', id=id)

def circuit_power_by_name(circuit_name):
    """Get the instantaneous power through a circuit.  The circuit
    must be named by the user-settable |circuit_name|, which is
    matched exactly.

    Since the Current Transformers (CTs) are sometimes installed
    backwards during panel installation (mine was!), the instantPowerW
    value could be negative (which do normally occur for circuits that
    might feed power back to the grid, e.g., solar), beware!  The
    caller should know whether negation or using the absolute value is
    appropriate for the circuit.
    """

    return circuit_attribute_value('instantPowerW', name=circuit_name)
