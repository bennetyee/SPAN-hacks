#!/usr/bin/python

# This set of utilities is an attempt to make a cleaner, more object
# oriented interface to getting access to a SPAN electrical panel.
# This started as code written on top of span.io's example code
# (mostly using span-curl via subprocess), and remains compatible with
# the data files created by that.  As a matter of face, as of this
# writing, this relies on the example code to generate the
# authentication token and populate the SPAN CA certificates
# directory (each panel is its own CA via leap-of-faith).


# Sources:
#  git@github.com:spanio/SPAN-API-Client-Docs.git
# see also
#  git@github.com:SpanPanel/span-panel-api.git
# for async MQTT interfaces

import json
import os
import pathlib
import requests
import subprocess
import sys
import time

class SpanError(Exception):
    pass

# Compatible with span.io's SPAN-API-Client-Docs.

def span_cert_dir():
    p = os.environ.get('SPAN_CA_CERT_DIR')
    if p:
        return pathlib.Path(p).expanduser()
    return pathlib.Path.home() / '.span-ca-certs'

def span_cert_path(serialnum):
    return span_cert_dir() / f'{serialnum}.crt'

def span_auth_path():
    p = os.environ.get('SPAN_AUTH_FILE')
    if p:
        return pathlib.Path(p).expanduser()
    return pathlib.Path.home() / '.span-auth.json'


class Panel:
    def __init__(self, serial, info):
        self._serial = serial
        self._info = info
        self._session = requests.Session()
        self._session.headers.update({'Authorization': f'Bearer {self.token()}'})

    # sanity checks should not be necessary if object was created via
    # AuthInfo's panel_info

    def serial(self):
        return self._serial

    def hostname(self):
        if 'hostname' not in self._info:
            raise SpanError(f'panel info does not have a hostname')
        return self._info['hostname']

    def token(self, panel=None):
        if 'access_token' not in self._info:
            raise SpanError(f'panel info does not contain access token')
        return self._info['access_token']

    def request_params(self, pathspec, use_tls):
        h = self.hostname()
        if use_tls:
            url = f'https://{h}{pathspec}'
            v = span_cert_path(self._serial)
        else:
            url = f'http://{h}{pathspec}'
            v = None
        return (url, v)

    def get(self, pathspec, use_tls=True):
        """Returns a requests module Response object.  Since we do not
        use stream=True, there is (currently) no need to explicitly
        invoke close() or del() the object.

        """
        url, v = self.request_params(pathspec, use_tls)
        return self._session.get(url, verify=v)

    def post(self, pathspec, payload, use_tls=True):
        url, v = self.request_params(pathspec, use_tls)
        return self._session.post(url, data=payload, verify=v)

class AuthInfo:
    def __init__(self, span_auth, panel = None):
        try:
            with open(span_auth, 'r') as f:
                d = json.load(f)
        except json.JSONDecodeError as e:
            raise SpanError(f'file {span_auth} json decode problem: {e}')
        if 'default_panel' not in d and panel is None:
            raise SpanError(f'auth info in file {span_auth} does not contain a default panel, and no panel override is specified')
        if panel is None:
            panel = d['default_panel']
        if 'panels' not in d:
            raise SpanError(f'auth info in file {span_auth} does not list any panels')
        self._default_panel = panel
        self._panels = d['panels']
        if panel not in self._panels:
            raise SpanError(f'panel {panel} not in list of panels {', '.join(self._panels.keys())}')
        # sanity checks
        for p in self._panels.keys():
            info = self.panel_info(p)
            if 'hostname' not in info._info:
                raise SpanError(f'panel {p} does not have a hostname')
            if 'access_token' not in info._info:
                raise SpanError(f'panel {p} does not have an access token')

    def panel_info(self, panel=None):
        if panel is None:
            panel = self._default_panel
        if panel not in self._panels:
            raise SpanError(f'requested panel {panel} not in list of panels {', '.join(self._panels.keys())}')
        return Panel(panel, self._panels[panel])

    def panel_hostname(self, panel=None):
        return panel_info(panel).hostname()

    def panel_token(self, panel=None):
        return panel_info(panel).token()


# this should be done entirely in python rather than using an external
# process
def span_curl(api):
    d = subprocess.run(['span-curl', api], capture_output=True, text=True)
    return (d.stdout, d.returncode)

def get_circuits():
    data, status = span_curl('/api/v1/circuits')
    if status == 0:
        try:
            d = json.loads(data)
        except json.JSONDecodeError as e:
            sys.stderr.write(f'get_circuits: json error {e}\n')
            return None
        if 'circuits' not in d:
            return None
        return d['circuits']
    return None

def get_one_circuit(id):
    data, status = span_curl(f'/api/v1/circuits/{id}')
    if status == 0:
        try:
            d = json.loads(data)
        except json.JSONDecodeError as e:
            sys.stderr.write(f'get_one_circuit: json error {e}\n')
            return None
        return d
    return None

def get_circuit_info_by_id(id):
    """Get the info json dict for a circuit.  The circuit must be
    identified by the its unique |id| (long hex string).

    """

    return get_one_circuit(id)

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
