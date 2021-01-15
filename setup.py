#!/usr/bin/env python3
from setuptools import setup, find_packages, find_namespace_packages

setup(
    name='charge-lnd',
    version='0.1.0',
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
