#!/usr/bin/env python
import os
from setuptools import setup, find_packages

f = open(os.path.join(os.path.dirname(__file__), 'README.md'))
readme = f.read()
f.close()

setup(
    name='django-class-fixtures',
    version='0.9a1',
    description='django-class-fixtures is a reusable Django application that '
        'enables the use of class-based fixtures alongside traditional '
        'serialized files for tests and initial data.',
    long_description=readme,
    author='JK Laiho',
    author_email='jklaiho@iki.fi',
    url='http://github.com/jklaiho/django-class-fixtures/tree/master',
    packages=find_packages(),
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    test_suite='class_fixtures.tests.runtests.runtests'
)
