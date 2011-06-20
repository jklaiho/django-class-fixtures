Installation
============

Dependencies:

* Python 2.6+
* Django 1.2+

Until version 1.0 is released (see :ref:`future` for details),
django-class-fixtures will only be available through a GitHub source checkout.
Post-1.0, you can get it off PyPi using ``easy_install`` or ``pip``.

The GitHub page for this project is at
https://github.com/jklaiho/django-class-fixtures. Once you've grabbed the
source, run ``sudo python setup.py install`` (you can most likely drop the
``sudo`` if you're using ``virtualenv``).

To avoid waking up screaming in the middle of the night, you can run the
test suite either with ``python setup.py test`` from the initial source
checkout, or with ``python manage.py test class_fixtures`` from inside a
Django project directory, once you've got one up and running.