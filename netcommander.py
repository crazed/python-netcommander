import collections
import io
import json
import os
import requests
import urllib2
import ssl

from lxml import etree
from StringIO import StringIO
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

NETCONF_PROXY_ENDPOINT = os.environ.get('NETCONF_PROXY_ENDPOINT', 'http://localhost:8080/netconf')
SSL_ASSERT_HOSTNAME = os.environ.get('SSL_ASSERT_HOSTNAME', True)

if SSL_ASSERT_HOSTNAME in ['false', '0', 0]:
    SSL_ASSERT_HOSTNAME = False

class MoreSecureAdapter(HTTPAdapter):
    """
    The netconf_proxy TLS server only implements TLSv1, on some systems
    the default is to try SSLv2 first, which will fail. The SSL_ASSERT_HOSTNAME
    environment variable can be used to turn off strict hostname checking.
    """
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       assert_hostname=SSL_ASSERT_HOSTNAME,
                                       ssl_version=ssl.PROTOCOL_TLSv1)

class Credentials(object):
    """
    This can be subclassed to create custom credential stores
    """
    def __init__(self, username, password, port=22):
        self.username = username
        self.password = password
        self.port = port

class DictMixin(collections.MutableMapping):
    def __init__(self):
        self._dict = {}

    def __iter__(self):
        return iter(self._dict)

    def __contains__(self, value):
        return value in self._dict

    def __len__(self):
        return len(self._dict)

    def __setitem__(self, key, item):
        self._dict[key] = item
        return

    def __delitem__(self, item):
        del self._dict[item]
        return

    def __getitem__(self, item):
        return self._dict[item]

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__,
                             ', '.join(self._dict.keys()))

class Device(DictMixin):
    def __init__(self, hostname, **kwargs):
        self.hostname = hostname
        self._dict = kwargs

    def __repr__(self):
        return "<%s(%s %s)>" % (self.__class__.__name__, self.hostname,
                                self._dict)

class Devices(DictMixin):
    def append(self, device):
        self._dict[device.hostname] = device
        return

    @property
    def hostnames(self):
        return self._dict.keys()

class MetaStore(object):
    def search(self, *args, **kwargs):
        """
        This is expected to return a Devices object populated with Device
        objects that match an arbitrary search.
        """
        pass

class Manager(object):
    def __init__(self, endpoint=NETCONF_PROXY_ENDPOINT, store=None, creds=None):
        self._endpoint = endpoint
        self._store = store
        self._credentials = creds
        self._session = requests.Session()
        self._session.mount('https://', MoreSecureAdapter())

    def set_credentials(self, creds):
        self._credentials = creds

    def set_store(self, store):
        self._store = store

    def search(self, *args, **kwargs):
        return self._store.search(*args, **kwargs)

    def run_rpc(self, tree, devices):
        """
        This simply appends the rpc tag to the supplied tree, and removes the rpc-reply
        tag from the response.
        """
        # Handle raw XML strings being passed here
        if not etree.iselement(tree):
            tree = etree.fromstring(tree)

        rpc = etree.Element('rpc')
        rpc.append(tree)
        for data in self.run(rpc, devices):
            data['Output'] = data['Output'][0]
            yield data

    def run(self, tree, devices):
        payload = {'username': self._credentials.username,
                   'password': self._credentials.password,
                   'port': self._credentials.port,
                   'hosts': devices.hostnames,
                   'request': etree.tostring(tree)}
        req = self._make_request(json.dumps(payload))
        resp = self._session.send(req, stream=True)

        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                data['Output'] = self._parse_xml(data['Output'])
                yield data

    def _parse_xml(self, string):
        """
        This is a wrapper around lxml to run an xslt transform which
        removes any namespaces provided.
        """
        xslt = """
        <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
        <xsl:output method="xml" indent="no"/>

        <xsl:template match="/|comment()|processing-instruction()">
            <xsl:copy>
                <xsl:apply-templates/>
            </xsl:copy>
        </xsl:template>

        <xsl:template match="*">
            <xsl:element name="{local-name()}">
                <xsl:apply-templates select="@*|node()"/>
            </xsl:element>
        </xsl:template>

        <xsl:template match="@*">
            <xsl:attribute name="{local-name()}">
                <xsl:value-of select="."/>
            </xsl:attribute>
        </xsl:template>
        </xsl:stylesheet>
        """
        parser = etree.XMLParser(remove_blank_text=True)
        xslt_doc = etree.parse(io.BytesIO(xslt), parser)
        transform = etree.XSLT(xslt_doc)
        root = etree.fromstring(str(transform(etree.parse(StringIO(string)))))
        return root


    def _make_request(self, data=None):
        headers = {'accept': 'application/json',
                   'user-agent': 'python-netcommander',
                   'connection': 'keep-alive'}
        return requests.Request('POST', self._endpoint,
                                headers=headers, data=data).prepare()
