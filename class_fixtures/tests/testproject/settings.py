import os
import sys

parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")
sys.path.insert(0, parent)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'testproject.db',
    }
}

SECRET_KEY = '215e15dfu^)2)mn1e5660f+%52*c141x=hzgpl@!4t-iv&n^iy'

ROOT_URLCONF = 'testproject.urls'

INSTALLED_APPS = (
    'class_fixtures',
    'class_fixtures.tests',
)

SERIALIZATION_FORMATS = {
    'class': 'class_fixtures.serializer'
}