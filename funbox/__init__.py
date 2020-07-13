#!/usr/bin/env python

import logging
import requests


logger = logging.getLogger(__name__)


class FunBoxError(Exception):
    pass


class SysBusError(FunBoxError):
    pass


class FunBox:
    def __init__(self, address, username, password):
        self.address = address.rstrip('/') + '/'
        self.username = username
        self.password = password
        self.session = requests.Session()

    def login(self):
        resp = self.session.post(
            self.address + 'authenticate',
            params={'username': self.username, 'password': self.password})
        if resp.status_code != 200:
            raise LoginError(resp.status_code, resp.reason)
        data = resp.json()
        assert data['status'] == 0
        skeys = [c.split('/')[0]
                 for c in resp.cookies.keys()
                 if c.endswith('/sessid')]
        (skey,) = skeys
        context_id = data['data']['contextID']
        self.session.cookies.set(f'{skey}/context', context_id)
        self.session.headers['X-Context'] = context_id

    def sysbus(self, path, params=None, retries=1):
        url = self.address + 'sysbus/' + path
        logger.debug('POST %s %r', url, params)
        resp = self.session.post(url, json={'parameters': params or {}})
        assert resp.status_code == 200
        jresp = resp.json()
        logger.debug('response: %r', jresp)
        if 'result' in jresp:
            jresp = jresp['result']
        if 'errors' not in jresp:
            return jresp
        if jresp['errors'][0]['error'] == 13 and retries:
            self.login()
            return self.sysbus(path, params=params, retries=(retries-1))
        raise SysBusError(jresp['errors'])

    def get_wan_status(self):
        return self.sysbus('NMC:getWANStatus')['data']

    def get_lan_ip(self):
        return self.sysbus('NMC:getLANIP')['data']

    def sysinfo(self):
        return self.sysbus('Devices/Device/HGW:get')['status']

    def reboot(self):
        return self.sysbus('NMC:reboot')
