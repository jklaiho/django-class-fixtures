Configuration
=============

There's not much of it.

After installing django-class-fixtures into your Python environment, insert
``class_fixtures`` into ``INSTALLED_APPS`` in the settings file of your Django
project. Doesn't matter where. All this does is override the ``loaddata``
management command with a version that supports class-based fixtures. No
models are installed, so no need for ``syncdb`` or schema migrations.

.. note:: No other ``loaddata``-overriding apps should be present in
    ``INSTALLED_APPS``. Depending on the order of the apps listed there,
    django-class_fixtures' override may not end up being the active one, and
    your class-based fixtures won't get loaded. Even if it is the active one,
    then your *other* ``loaddata`` override won't work, which is probably not
    what you want either.

If you wish to place fixtures outside of the ``fixtures`` directories of your
Django apps (i.e. use "project-level" fixtures), use the ``FIXTURE_PACKAGES``
setting, an iterable similar to Django's own ``FIXTURE_DIRS``, only containing
dotted-path notation to Python packages containing fixture modules.

Example::

    FIXTURE_PACKAGES = (
        'myproject.something.fixtures',
        'someplace.other.project_fixtures',
    )

Obviously, the module paths listed must be valid and importable in the Python
environment that your Django project lives in. Make sure they have
``__init__.py`` modules.

With that out of the way, check out the :doc:`introduction` guide to, well,
get started.
