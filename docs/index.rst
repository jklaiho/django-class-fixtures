Welcome to django-class-fixtures!
=================================

The purpose of django-class-fixtures is to augment Django's fixture system,
used for loading initial data during ``manage.py syncdb`` calls, test data
with the ``TestCase.fixtures`` iterable, and other types of data with manual
invocations of ``manage.py loaddata``.

While still supporting Django's traditional model serialization formats,
django-class-fixtures provides pure Python **class-based fixtures**. They take
the form of model instance definitions in a syntax that is very close to how
you'd create new instances with ``SomeModel.objects.create(**kwargs).`` The
thinking goes: why do fixtures in JSON, XML or YAML, when you could just as
well do it all with Python code?

This initial public release, 0.8, only implements the **loading** of
class-based fixtures through a ``loaddata`` override. The fixtures have to be
created by hand until the release of version 0.9, which brings ``dumpdata``
support and is the first version I'd expect anyone besides myself to actually
use in real-world projects. See :ref:`future` for details on future versions.

Even though 0.8 already has rather decent test coverage, use it at your own
risk. The first somewhat safe production version will be 1.0. The standard
non-liability clauses in ``LICENSE.txt`` apply then as well, of course.

See :doc:`introduction` for an introduction. After that, check out
:doc:`using` for some additional information about the capabilities of
django-class-fixtures, and some neat tricks that class-based fixtures enable
you to pull off.

Good luck!

----

.. toctree::
    :maxdepth: 2
    
    installation
    configuration
    introduction
    using
    moreinfo
    design
    changelog