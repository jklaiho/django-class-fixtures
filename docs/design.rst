Design Choices and Constraints
==============================

This section outlines some of the design choices made during the development
of django-class-fixtures.

As a general rule, django-class-fixtures tries to work as much like Django's
fixture loading mechanisms as possible or feasible. **Predictability** is the
key: if you're used to working with Django's fixture system,
django-class-fixtures should minimize any surprises.

.. _hardcoded:

Hard-coded primary keys
-----------------------

Using Python objects instead of serialized JSON files as the data source for
the ``loaddata`` command, an option exists to not force the use of hard-coded
primary keys. Relations from objects in class fixtures could easily be made
both to other class fixtures and objects that already exist in the database
prior to the loading of the fixture (such as content types created during
``manage.py syncdb``).

In fact, early development versions of django-class-fixtures took this exact
approach, using special objects called "relation tokens" and kwarg-based
deferred object searches to build relations and their associated loading order
dependency graphs.

While reasonably elegant, this approach posed several problems. First was the
fact that django-class-fixtures needed to work with old-style serialized
fixture files that do have hard-coded keys. Mixing hard-coded PKs with
dynamically assigned primary keys is a recipe for disaster. This was
circumvented by making sure that old-style fixtures always got loaded first,
ensuring that class fixtures would not get overwritten and that relations
didn't go haywire. Some dangers still remained, but this could be overcome
with sufficient guidance of best practices in the documentation.

Another issue was that of code complexity. While hard-coding primary keys into
Python code "feels dirty", doing so enables the code of django-class-fixtures
to be a lot simpler and more terse, doing away with a lot of corner case
handling and object identification needed for building relations.

The final nail in the coffin was the fact that if fixtures don't hard-code
primary keys, then successive ``loaddata`` calls create duplicate objects
instead of overwriting existing ones. Without a primary key, there was no
reliable way of identifying if the object that a class fixture represents
already existed in the database or not. While creating duplicate objects isn't
"wrong" in an absolute sense, at least not much more than blindly overwriting
any changes in existing objects (which is what Django does), the initial
design choice to be predictable for users of old-style fixtures made it
necessary to hard-code primary keys into class fixtures as well.

I wish it wasn't so, but then again, I wish for a lot of things that I can't
have. If you discover a way to do it properly, do tell.

.. _locations:

Fixture locations
-----------------

Since class fixtures are Python objects, theoretically you could have a lot of
flexibility with their placement, how to import them etc. But as Django
expects apps to have ``fixtures`` subdirs containing serialized files,
django-class-fixtures expects modules containing class fixtures to be there as
well. The only difference is that ``fixtures`` must also contain an
``__init__.py`` module, turning the directory into a Python package.
Serialized fixtures in the same directory will continue to work as before,
since Django's ``loaddata`` only cares about the non-Python files inside it.

This "transparent" approach won't work with directories defined in
``FIXTURE_DIRS``, however. It's an iterable of filesystem paths that—unlike
app-based ``fixtures`` dirs—may not lie on Python's module search path at all,
and even if they did, converting filesystem paths into importable module paths
would be extremely impractical.

The ``FIXTURE_DIRS`` use case of having fixtures outside the apps is a valid
one, so our own ``FIXTURE_PACKAGES`` setting aims to enable the same way of
storing class fixture modules.

Just as Django's ``loaddata`` only looks at fixtures that are in the
``fixtures`` dir itself, not any subdirectories, our ``loaddata`` only
discovers and uses fixture modules in the ``fixtures`` package. Nothing stops
you from creating subpackages like ``fixtures.regressiontests`` from which you
import stuff into modules contained directly under ``fixtures``, of course.