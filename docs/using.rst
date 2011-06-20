Using class-based fixtures
==========================

Since django-class-fixtures provides a drop-in replacement for Django's
``loaddata``, you use it exactly as you would Django's fixtures, but with a
few bonuses.

Tests
-----

As you probably know, to use fixtures in Django, you set up
``TestCase.fixtures``, like so::

    class WhatLovelyTests(TestCase):
        fixtures = ["something", "other_things.json"]
        
        def test_random_stuff(self):
            (...)

``TestCase.fixtures`` is an iterable of strings, corresponding to fixture file
names (with or without specifying the extension), located under the
``fixtures`` directory of any app, or within any directory listed in
``settings.FIXTURE_DIRS``. Django loads all fixtures with those names that it
can find.

.. note::
    One exception, which you know if you've learned Django's documentation on
    the topic: you can't have ``something.json`` **and** ``something.xml``
    inside the ``fixtures`` directory of the same app and then refer to plain
    ``"something"`` inside ``TestCase.fixtures``. Having those in two separate
    apps works fine and loads both, though.

.. _testcasefixtures:

That same example works as-is under our ``loaddata`` override, but
django-class-fixtures allows you to put some other things in
``TestCase.fixtures`` as well::

    from wage_slave.fixtures.some_module import employees
    from bandaid.fixtures import other_bands
    
    class ClassFixtureUsingTests(TestCase):
        fixtures = [
            employees, # 1
            other_bands, # 2
            "some_app_name", # 3
            "another_app.assorted_fixtures", # 4
            "something" # 5
        ]

1. An individual :class:`Fixture` instance cherry-picked from its containing
   fixture module.
2. An individual fixture module. All :class:`Fixture` instances contained
   within it are loaded.
3. The name of an app in ``settings.INSTALLED_APPS``. All of its class-based
   fixtures are loaded in whatever order they are discovered. Traditional
   Django fixtures in that app are **not** loaded.
4. An "appname.fixture_module_name" string. This is an alternative to #2 that
   doesn't require you to import the fixture module. In this example, a
   fixture module called ``assorted_fixtures.py`` must reside in the
   ``fixtures`` subpackage/directory of ``another_app``.
5. The name of a fixture module in one of the fixture directories.

Astute readers will have spotted a slight problem with #3, #4 and #5. Being
strings, all would also be valid Django fixture names, and Django's
``loaddata`` would search for ``some_app_name.(format)``,
``another_app.assorted_fixtures.(format)`` and ``something.(format)`` files,
substituting (format) for all the supported serialization formats. So what
gets loaded in case of duplicate names? This is covered in
:ref:`loadingrules`. Of course, it helps if you don't mix traditional and
class-based fixtures, if you can avoid it.

Initial data
------------

By now, you may have guessed how initial data works. You stick your
:class:`Fixture` instances in a file called ``initial_data.py``, and that's
pretty much all there is to it. It will get loaded with ``syncdb``.

In case you have both ``initial_data.json`` and ``initial_data.py`` in the
same fixture directory/package, both will be loaded. The traditional JSON
fixture will always be loaded first.

Manual ``loaddata`` calls
-------------------------

When running ``python manage.py loaddata`` with the name of a fixture on the
command line, you obviously can't pass in a :class:`Fixture` instance or an
imported fixture module like you can in ``TestCase.fixtures``. But in addition
to the name of a fixture module, passing in the name of an app or an
"appname.fixture_module_name" works (as described in options 3 to 5 in
:ref:`the ways of using TestCase.fixtures <testcasefixtures>` above).

Loading traditional Django fixtures works like before.

.. _dynamicfixtures:

Dynamic approaches to fixture creation
--------------------------------------

It would be boring if django-class-fixtures didn't have any tricks up its
sleeve. Here's a couple of ways to use the fact that the fixtures are just
Python to your advantage.

.. _structureddata:

Looping through structured data to create fixtures
##################################################

Say you're tired of manually defining the primary keys for each model instance
you add to a fixture. Well, here's a way of being a bit more terse, defining
the field names just once instead of writing them out in every :func:`add`
call, and automatically generating the required primary keys in situations
when you know it's safe::

    field_names = ("name", "genre")
    data = [
        ("Bar Fighters", "Rock"),
        ("Brutallica", "Metal"),
        ("Led Dirigible", "Rock")
    ]

    bands = Fixture(Band)
    for i in range(len(data)):
        bands.add(i+1, **dict(zip(field_names, data[i])))

For a simplistic model like ``Band`` and such few instances, the above
technique is a bit overkill. But for adding large amounts of instances of big
models with more fields, it enables you to produce a lot less code.

.. note::
    The above method is, in fact, one I've considered the ``dumpdata``
    override coming in version 0.9 to use. To make it a bit cleaner, I may add
    a helper method to ``Fixture`` instances that takes the field name tuple
    and the data tuple as its parameters directly, doing the zip-dict dance
    internally.

The underlying point is to illustrate how you're not stuck with the canonical
fixture construction method described in the examples around the
documentation.

.. _projectleveldata:

Inserting project-level data into app-level fixtures
####################################################

One useful way of doing something beyond the capabilities of Django's
serialized fixtures is to determine the data that :class:`Fixture` instances
contain at runtime.

The fixture discovery process doesn't care what else the fixture modules
contain besides :class:`Fixture` instances, so you can do all sort of coding
gymnastics to produce the data contained in them.

One example: say you work at a company constructing e-commerce sites, each of
which uses a payment processing app built in-house. Each site uses different
merchant IDs and other content related to the payment processing app that you
want stored in the database.

Since the app is reusable across sites, you'd like it to contain fixtures that
you can configure on the project (i.e. site) level. You create a single data
source per site in a predefined location (say,
``projectfolder/site_customize``), from which the objects contained in the
app-level :class:`Fixture` instances get their site-specific data. Less
custom settings, no site-specific modifications to the fixtures of the
payment app. (This is functionality I wish I'd had at my fingertips on some
previous projects.)

This is achievable by making the fixture module import the relevant data
structures from a preset site-level location. Here's a simplified example,
using two imaginary e-commerce sites, Cheese Emporium and Snake World, and
their project-level customization for a payment app called Moolah::

    # cheese_emporium/site_customize/payment.py
    paypal_merchant_id = 12534768abcd
    google_checkout_merchant_id = asdfqwerty
    
    # snake_world/site_customize/payment.py
    paypal_merchant_id = 87654321dcba
    google_checkout_merchant_id = qwertyasdf
    
    # In the fixture module, moolah/fixtures/merchant_data.py
    # Determine what the project's root path is through a setting or 
    # something, import site_customize.payment from it.
    processors = Fixture(PaymentProcessor)
    processors.add(1, name="PayPal", merchant_id=payment.paypal_merchant_id)
    processors.add(2, name="Google Checkout", merchant_id=payment.google_checkout_merchant_id)

No matter which site the app is attached to, the fixture module will insert
the correct data when loaded.

And more, much more!
####################

What else? Based on runtime conditions, leave out objects from, or add more
objects to a :class:`Fixture` instance, or determine what model to construct
the instance with in the first place. The payment processor example above
could easily be modified to only include PayPal for Cheese Emporium and Google
Checkout for Snake World, based on some factors set on the site level and
checked for in ``if`` clauses around the :func:`add` statements.

It is my sincere hope that django-class-fixtures enables its users to see
fixtures in a new light. Some interesting new possibilities are there to be
discovered.

Use your imagination. In the end, it's all just Python. Bend it to your will!

If you haven't already, now would be a good time to check out :doc:`moreinfo`.