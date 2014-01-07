import json
import os
import urllib2
import re

from netcommander import MetaStore, Device, Devices

OPTOPUS_ENDPOINT=os.environ.get('OPTOPUS_ENDPOINT')

class OptopusMetaStore(MetaStore):
    def __init__(self, endpoint=OPTOPUS_ENDPOINT):
        self._endpoint = endpoint
        self._client = Client(endpoint=self._endpoint)

    def search(self, query_string):
        devices = Devices()
        res = self._client.search(query_string, types=['network_node'])
        for data in res:
            device = Device(data['hostname'], **data['facts'])
            devices.append(device)
        return devices

class Client(object):
    def __init__(self, endpoint=OPTOPUS_ENDPOINT, dry_run=False):
        self._endpoint = endpoint
        self._dry_run = dry_run

    def search(self, string, types=None):
        path = "/api/search?string=%s" % urllib2.quote(string)
        if types:
            path += "&types=%s" % ','.join(types)
        return self._get(path)['results']

    def _get(self, path):
        req = urllib2.Request("%s%s" % (self._endpoint, path))
        req.add_header('Accept', 'application/json')
        req.add_header('User-agent', 'switcheroo')
        if self._dry_run:
            results = req.get_full_url()
        else:
            url = urllib2.urlopen(req)
            results = json.loads(url.read())
        return results
