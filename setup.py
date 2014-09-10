#!/usr/bin/env python
from setuptools import setup

setup(name='netcommander',
      version='1.6',
      description='A client library to use netconf_proxy',
      author='Allan Feid',
      author_email='allan@ops.guru',
      url='http://github.com/crazed/python-netcommander',
      packages=['netcommander', 'netcommander.optopus'],
      install_requires=['lxml', 'requests', 'xmltodict', 'wsgiref', 'distribute'],
     )
