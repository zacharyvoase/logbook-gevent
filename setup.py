#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages


setup(
    name='logbook-gevent',
    version='0.0.1',
    description='Greenlet-based context stack management for using Logbook with gevent.',
    author='Zachary Voase',
    author_email='z@zacharyvoase.com',
    url='http://github.com/zacharyvoase/logbook-gevent',
    py_modules=['logbook_gevent'],
    package_dir={'': 'lib'},
    install_requires=[
        'Logbook==0.3',
    ],
)
