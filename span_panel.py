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
    # AuthInfo's panel()

    def serial(self):
        return self._serial

    def hostname(self):
        if 'hostname' not in self._info:
            raise SpanError(f'Panel info does not have a hostname.')
        return self._info['hostname']

    def token(self, panel=None):
        if 'access_token' not in self._info:
            raise SpanError(f'Panel info does not contain access token.')
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
        try:
            return self._session.get(url, verify=v)
        except requests.exceptions.RequestException as e:
            raise SpanError(f'Panel get(): session transient error? ({e}).')

    def get_json(self, pathspec, use_tls=True):
        resp = self.get(pathspec, use_tls)
        if resp.status_code != 200:
            raise SpanError(f'Request of {pathspec} got unexpected HTTP response {resp.status_code}.')
        try:
            d = json.loads(resp.text)
        except json.JSONDecodeError as e:
            raise SpanError(f'Request of {pathspec} not JSON parsable: {e}.')
        return d

    def post(self, pathspec, payload, use_tls=True):
        url, v = self.request_params(pathspec, use_tls)
        return self._session.post(url, data=payload, verify=v)

    def post_json(self, pathspec, payload, use_tls=True):
        return self.post(pathspec, json.dumps(payload), use_tls)

    def get_circuits(self):
        pathspec = '/api/v1/circuits'
        jd = self.get_json(pathspec)
        if 'circuits' not in jd:
            raise SpanError(f'Panel {self.serial()} response to {pathspec} did not contain key "circuits".')
        return jd['circuits']

    def get_circuit_by_id(self, id):
        pathspec = f'/api/v1/circuits/{id}'
        jd = self.get_json(pathspec)
        return jd

    def get_circuit_by_name(self, name):
        circ = self.get_circuits()
        for id in circ.keys():
            info = circ[id]
            if 'name' in info and info['name'] == name:
                return info
        raise SpanError(f'Panel {self.serial()} has no circuit with name {name}.')

    def attribute_value(self, attribute, id = None, name = None):
        if id is None and name is None:
            raise SpanError(f'Invocation of attribute_value must specific exactly one of "id" or "name" keyword arguments. Both are None.')
        if id is not None and name is not None:
            raise SpanError(f'Invocation of attribute_value must specific exactly one of "id" or "name" keyword arguments. Both cannot be specified. (id={id}, name={name}.)')
        if id is not None:
            info = self.get_circuit_by_id(id)
        else:
            info = self.get_circuit_by_name(name)
        return info[attribute]

class AuthInfo:
    def __init__(self, span_auth = None, panel = None):
        if span_auth is None:
            span_auth = span_auth_path()
        try:
            with open(span_auth, 'r') as f:
                d = json.load(f)
        except json.JSONDecodeError as e:
            raise SpanError(f'File {span_auth} json decode problem: {e}.')
        if 'default_panel' not in d and panel is None:
            raise SpanError(f'Auth info in file {span_auth} does not contain a default panel, and no panel override is specified.')
        if panel is None:
            panel = d['default_panel']
        if 'panels' not in d:
            raise SpanError(f'Auth info in file {span_auth} does not list any panels.')
        self._default_panel = panel
        self._panels = d['panels']
        if panel not in self._panels:
            raise SpanError(f'Panel {panel} not in list of panels {', '.join(self._panels.keys())}.')
        # sanity checks
        for p in self._panels.keys():
            info = self.panel(p)
            if 'hostname' not in info._info:
                raise SpanError(f'Panel {p} does not have a hostname.')
            if 'access_token' not in info._info:
                raise SpanError(f'Panel {p} does not have an access token.')

    def panel(self, panel=None):
        if panel is None:
            panel = self._default_panel
        if panel not in self._panels:
            raise SpanError(f'Requested panel {panel} not in list of panels {', '.join(self._panels.keys())}.')
        return Panel(panel, self._panels[panel])

    def panel_hostname(self, panel=None):
        return self.panel(panel).hostname()

    def panel_token(self, panel=None):
        return self.panel(panel).token()

