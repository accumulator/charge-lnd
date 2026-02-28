#!/usr/bin/env python3
from setuptools import setup, find_packages, find_namespace_packages
import os
import re

def get_version():
    init_file = os.path.join(os.path.dirname(__file__), 'charge_lnd', '__init__.py')
    with open(init_file, 'r') as f:
        content = f.read()
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string")

setup(
    name='charge-lnd',
    version=get_version(),
    description='A simple policy based fee manager for LND',
    author='Sander van Grieken',
    author_email='sander@outrightsolutions.nl',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3'
        ],
    keywords='lightning, lnd, bitcoin',
    packages=find_packages(where='.') + find_namespace_packages(where='.', include=['charge_lnd*']),
    python_requires='>=3.6, <4',
    install_requires=['googleapis-common-protos','grpcio','protobuf','six','termcolor','colorama','aiorpcx'],
    entry_points={
        'console_scripts' : ['charge-lnd=charge_lnd.charge_lnd:main']
        },
    project_urls={
        'Bug Reports': 'https://github.com/accumulator/charge-lnd/issues',
        'Source' : 'https://github.com/accumulator/charge-lnd'
        }
)
