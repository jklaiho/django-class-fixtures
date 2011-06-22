#!/usr/bin/env python
import os
import sys

from django.conf import settings

class AlternateDBTestRouter(object):
    def allow_syncdb(self, db, model):
        """
        The ``Party`` and ``Politician`` objects in our initial_data
        (.py and .json) fixtures are not allowed to enter the "alternate"
        database.
        """
        if db == 'alternate':
            return model._meta.object_name not in ['Party', 'Politician']
        return None


if not settings.configured:
    settings.configure(
        DATABASES = {
            'default': {
                'NAME': 'primary',
                'ENGINE': 'django.db.backends.sqlite3',
            },
            'alternate': {
                'NAME': 'secondary',
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        DATABASE_ROUTERS = ['class_fixtures.tests.runtests.AlternateDBTestRouter'],
        INSTALLED_APPS = [
            'class_fixtures',
            'class_fixtures.tests',
            'class_fixtures.tests.testapp_no_fixtures',
        ],
        SERIALIZATION_FORMATS = {
            'class': 'class_fixtures.serializer'
        }
    )

from django.test.simple import DjangoTestSuiteRunner

def runtests(*test_args):
    if not test_args:
        test_args = ['tests']
    parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
    sys.path.insert(0, parent)
    failures = DjangoTestSuiteRunner(failfast=False).run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    runtests(*sys.argv[1:])
