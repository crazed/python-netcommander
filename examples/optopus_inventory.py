import netcommander
import optopus
import os

from lxml import etree

username = os.environ.get("USER")
password = os.environ.get("PASSWORD")
optopus_endpoint = os.environ.get("OPTOPUS_ENDPOINT")

store = optopus.OptopusMetaStore(endpoint=optopus_endpoint)
credentials = netcommander.Credentials(username, password)

manager = netcommander.Manager(store=store, creds=credentials)
devices = manager.search("ex2200 location:ma01 active:true")

for data in manager.run_rpc('<get-chassis-inventory/>', devices):
    print data['Hostname']
    print "=================================="
    print data['Output'].xpath('//chassis/description')[0].text
    print data['Output'].xpath('//chassis/serial-number')[0].text
    print ""

for data in manager.last_errors:
    print "%s: %s" % (data['Hostname'], data['Output'])
