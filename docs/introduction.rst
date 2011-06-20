Getting started
===============

If you're not familiar with Django's existing fixture system, please look at
the relevant Django documentation before going further. Things like why
fixtures exist, how and when they are used and what they are good for are not
covered here. Coming here, you've optimally used Django's fixtures for some
time and, if you're like me, gotten a little frustrated with them.

If you haven't already, have a quick look at the :doc:`configuration`
document. It's very short. All you need to do, basically, is to add
``class_fixtures`` to your ``INSTALLED_APPS``.

Let's dive in to the practical stuff right away.

Traditional fixtures vs. class-based fixtures
---------------------------------------------

We'll use a band-related Django app called *bandaid* and its models to 
illustrate the use of the basic features of django-class-fixtures.

Assume a simplistic Django model inside ``bandaid.models``, like this::

    class Band(models.Model):
        name = models.CharField(max_length=255)
        genre = models.CharField(max_length=100)

A typical way of creating an instance of this model would look like this::

    band = Band.objects.create(name="Bar Fighters", genre="Rock")

When serialized to JSON using the ``dumpdata`` management command, it would
look like this::

    [
        {
            "pk": 1,
            "model": "bandaid.band",
            "fields": 
            {
                "name": "Bar Fighters",
                "genre": "Rock"
            }
        }
    ]

That ``dumpdata`` output is saved as ``example_band.json`` inside
``bandaid/fixtures``. Our hypothetical *bandaid* app now looks like this::

    bandaid/
        __init__.py
        models.py
        fixtures/
            example_band.json

The JSON serialization of the ``Band`` object is simple enough, but files with
lots of serialized objects become cumbersome to deal with very quickly,
especially when using schema migrations. We'd rather just deal with Python
code all the way. It's more readable, as well as easier to modify by hand and
keep current with schema changes.

To that end, here's the code of a Python module. It contains a single
class-based fixture that contains a single object: a second instance of the
``Band`` model::

    from class_fixtures.models import Fixture
    from bandaid.models import Band
    
    bands = Fixture(Band)
    bands.add(2, name="Brutallica", genre="Metal")

That's it. Save that as ``more_bands.py`` in the *bandaid* app's ``fixtures``
directory. It becomes a *fixture module* that django-class-fixtures can use.
You're good to go.

Wait, not quite.

You'll notice that ``fixtures`` is a simple data directory inside the
*bandaid* app. It's not a Python package, which it needs to be for
django-class-fixtures to find any fixture modules inside it. This is easily
fixed: just add an ``__init__.py`` module inside it. The bandaid app now looks
like this::

    bandaid/
        __init__.py
        models.py
        fixtures/
            __init__.py
            example_band.json
            more_bands.py

Like magic, the sad and lonely ``fixtures`` directory is transformed into a
subpackage of the *bandaid* app where Python modules can be imported from. As
you can see, you can freely mix traditional serialized fixtures and
class-based fixtures. You just have to make sure that the primary keys (the
"pk" fields in JSON files and the first parameters to the :func:`add` calls in
fixture modules) don't conflict with each other.

.. note::
    A bit on terminology: in Django parlance, a "fixture" is the JSON/XML/YAML
    file containing serialized model objects, located inside one of the
    fixture directories.
    
    As for django-class-fixtures, a "fixture" is a single instance of the
    :class:`Fixture` class, many of which can and will appear inside a single
    *fixture module*, which is the actual .py file inside one of the fixture
    packages (i.e. directories with an ``__init__.py`` file).

All right, the basic infrastructure is in place. Let's look at what we just
did with the code in that fixture module.

Basic use of class-based fixtures
---------------------------------

First off, fixture modules need to import the :class:`Fixture` class from
``class_fixtures.models`` and any model classes that you want to create
fixtures for.

.. note::
    While the :class:`Fixture` class lives in ``class_fixture.models``, it's
    not a Django model class. It's model-related, though, and since Django
    apps need to have a ``models.py`` file anyway, it's as good a place as any
    for it.

Each :class:`Fixture` instance is attached to a model class by giving the model as
the first parameter to :class:`Fixture`, like ``Fixture(Band)`` above. For purposes
of organization or clarity, you can have multiple :class:`Fixture` instances per
model class::

    decent_bands = Fixture(Band)
    awful_bands = Fixture(Band)

Actually populating the :class:`Fixture` instances with objects is done using the
:func:`add` method. First, you give it the primary key and then, as keyword
arguments, the same arguments you'd give a ``Band.objects.create()`` call::

    decent_bands.add(3, name="Led Dirigible", genre="Rock")
    awful_bands.add(4, name="Flaxxid Bizkit", genre="Crap")
    
Note that the primary keys must keep incrementing across :class:`Fixture`
instances, since both of them are still going to create ``Band``
objects into the same database table.

.. note::
    If you are curious as to why the primary key needs to be hard-coded,
    see :ref:`hardcoded`. It's not necessary for learning how class-based
    fixtures work, though, so if this is your first time around, it's best to
    just keep moving for now.

Of course, eventually you'll have to create relations between objects.

You'll be doing two kinds of relations with fixtures:

1. Relations to objects that do not yet exist in the database, but are instead
   created in the same fixture module as the objects that point to them.
2. Relations to objects that exist in the database prior to ``loaddata`` being
   run (e.g. objects defined in ``initial_data`` fixtures created during
   ``syncdb``).

Let's look at these in that order.

Relationships between objects inside the same fixture module
------------------------------------------------------------

We'll start with foreign keys and these two example models from a hypothetical
app called *wage_slave*::
    
    class Company(models.Model):
        name = models.CharField(max_length=100)

    class Employee(models.Model):
        name = models.CharField(max_length=100)
        company = models.ForeignKey(Company)
        manager = models.ForeignKey('self', null=True)

We'll let code speak for itself first and then explain::

    from class_fixtures import Fixture
    from wage_slave.models import Company, Employee
    
    companies = Fixture(Company)
    employees = Fixture(Employee)
    
    companies.add(1, name="FacelessCorp Inc.")
    employees.add(1, name="Ty Rant", company=companies.fk(1))
    employees.add(2, name="Sue Ecide-Risk", company=companies.fk(1), manager=employees.fk(1))

As is hopefully apparent, we're creating one ``Company`` and two
``Employee``\s, one of which is the manager of the other one. The above
demonstrates both a foreign key to another model (the ``company`` of both
employees) and a recursive FK to the same model (Sue's ``manager``). This is
done using the :func:`fk` method of the target fixture instance, giving it the
primary key.

.. note:: An aside: which would you rather look at and deal with: those
    few rows of Python, or their imagined JSON representations? Just sayin'.

Due to the foreign key to ``Company``, ``Employee`` objects depend on their
target ``Company`` instances existing before they are defined. :class:`Fixture`
instances handle dependency resolution behind the scenes, so as long as you
have created the ``companies`` and ``employees`` instances first, it doesn't
matter in what order you :func:`add` the actual model instance definitions to
them. The proper loading order is determined automatically.

One-to-one relations work basically identically to foreign keys. To
demonstrate, here's one more model::

    class EmployeeHistory(models.Model):
        employee = models.OneToOneField(Employee)
        date_joined = models.DateField()

Using that model in the above scenario is as simple as you might guess::
    
    # Remember to add EmployeeHistory to the import from wage_slave.models
    histories = Fixture(EmployeeHistory)
    histories.add(employee=employees.o2o(1), date_joined='2003-03-15')

The :func:`o2o` method works identically to :func:`fk`. In fact, internally
it's the very same method, just a different alias. Picking the right one just
makes fixture code more self-documenting.

The implicit OneToOneFields created by concrete model inheritance don't need
explicit :func:`o2o` usage. Here's an example with an additional model that
inherits from ``bandaid.Band``::
    
    # in bandaid.models
    class MetalBand(Band):
        leather_pants_worn = models.BooleanField(default=False)
    
    # in some fixture module
    metalbands = Fixture(MetalBand)
    metalbands.add(666, name="Judas Bishop", genre="Metal", leather_pants_worn=True)

Nothing too special happens here; it relies on Django's model inheritance
functionality, where creating a ``MetalBand`` object will automatically create
a ``Band`` object with the same primary key. You just need to be careful to
not overlap the primary keys of any of the previously defined ``Band``
objects.

What about Many-to-many relationships? To demonstrate their use, we'll add a
few more models to the *bandaid* app::

    class Musician(models.Model):
        name = models.CharField(max_length=100)
        member_of = models.ManyToManyField(Band, through='Membership')

    class Membership(models.Model):
        musician = models.ForeignKey(Musician)
        band = models.ForeignKey(Band)
        instrument = models.CharField(max_length=100)

    class Roadie(models.Model):
        name = models.CharField(max_length=100)
        hauls_for = models.ManyToManyField(Band)

Again, let's look at some code first. Here's a revised form of
``bandaid.fixtures.more_bands``::

    from class_fixtures import Fixture
    from bandaid.models import Band, Musician, Membership, Roadie
    
    bands = Fixture(Band)
    musicians = Fixture(Musician)
    memberships = Fixture(Membership)
    roadies = Fixture(Roadie)
    
    bands.add(2, name="Brutallica", genre="Metal")
    bands.add(3, name="Led Dirigible", genre="Rock")
    bands.add(4, name="Flaxxid Bizkit", genre="Crap")
    musicians.add(1, name="Lars Toorich")
    # A "through" M2M, musician-to-band-via-membership
    membership.add(1, musician=musicians.fk(1), band=bands.fk(2), instrument="Bongos")
    # A normal M2M
    roadies.add(1, name="Tats Brimhat", hauls_for=[bands.m2m(2)])

Not many surprises there. "Through" M2Ms are just a couple of foreign keys in
the "middle" model in addition to any extra fields. The only thing of note is
the direct assignment of a single-item list to the ``hauls_for``
ManyToManyField to create the M2M relation between Roadie and Band. We just
inline the M2M relation directly to the object definition, just like with
foreign keys earlier.

This is in contrast to Django, where you'd do the same like this::

    brutallica = Band.objects.create(name="Brutallica", genre="Metal")
    tats = Roadie.objects.create(name="Tats Brimhat")
    # Either...
    tats.hauls_for.add(brutallica)
    # Or...
    brutallica.roadie_set.add(tats)

So, to create the M2M relation using Django's ORM, you need an extra call to
the ``add()`` method of the ManyRelatedManager (``hauls_for`` or
``roadie_set``, respectively) after creating the objects that relate to each
other.

M2M relations, of course, can be defined from either end of the relation.
This means that the following is also legal, and equivalent to
the earlier example of creating the roadie-band relation inline::
    
    # Create the M2M relation from the other end, i.e. the "target" of the
    # Roadie.hauls_for ManyToManyField. As you'll recall, the add() statements
    # can be in any order, so we can call roadies.m2m(1) before a Roadie with
    # that primary key is added to the "roadies" Fixture instance.
    bands.add(2, name="Brutallica", genre="Metal", roadie_set=[roadies.m2m(1)])
    roadies.add(1, name="Tats Brimhat")

The argument to M2M fields needs to be an iterable, even if it just has the
one element. To create several M2M relations, you just add elements to the
iterable. For example, to create a severely overworked roadie for a bunch of
bands::

    roadies.add(1, name="Tats Brimhat", hauls_for=[
        bands.m2m(2),
        bands.m2m(3),
        bands.m2m(4),
    ])

As it happens, :func:`m2m` is also just an alias of :func:`fk` and
:func:`o2o`. Internally, a special object called a *delayed related object
loader* is created for all three relation types, and resolved to actual
objects later on in the loading process.

Relations from fixture modules to pre-existing objects
------------------------------------------------------

Sometimes you'll need to define relations to objects that you know to exist in
the database prior to the loading of your fixture module. Syntax-wise, this is
actually somewhat simpler than the intra-module relations presented under the
previous heading.

Those pre-existing objects could be coming from ``syncdb`` calls that load
initial data, or from old-style Django-serialized fixtures that got loaded
before our class-based fixture did, or even from other class-based fixture
modules, ones we know to be loaded beforehand.

In our case, the *bandaid* app contains a single ``Band`` object serialized
into the ``example_band.json`` file under ``bandaid/fixtures``. We'll assume
that it was loaded first, and create a relation to it inside the
``more_bands.py`` fixture module like this::

    musicians.add(2, name="Dave Growl")
    # "Bar Fighters" in example_band.json has 1 as its primary key
    memberships.add(2, musician=musicians.fk(2), band=1, instrument="All of them")

As you can see from the ``band`` argument, instead of referring to the primary
key of a not-yet-created object through the :func:`fk` method of the
target :class:`Fixture` instance (like ``musicians.fk(2)``), you just give it the
primary key of the pre-existing related object directly.

.. note::
    Relations to pre-existing objects using natural key tuples instead of
    primary keys are covered in :ref:`naturalkeys` in the :doc:`moreinfo`
    document.

Or, you can just retrieve the actual model object inside the fixture module
and relate to that. This is an alternative to the previous example::

    bf = Band.objects.get(name="Bar Fighters")
    musicians.add(2, name="Dave Growl")
    memberships.add(2, musician=musicians.fk(2), band=bf, instrument="All of them")

M2Ms work no different. Assuming we had some other JSON fixture that defined
bands with PKs 5 and 6, we'd just do this to relate to them inside our
fixture module::

    roadies.add(2, name="Ciggy Tardust", hauls_for=[5,6])
    
    # or, if we wish to relate to the actual objects,
    # perhaps not even knowing or caring what the PKs are:
    
    some_band = Band.objects.get(**some_kwargs)
    other_band = Band.objects.get(**other_kwargs)
    roadies.add(2, name="Ciggy Tardust", hauls_for=[some_band, other_band])

This business with creating relations to objects outside the current fixture
module brings up a point that bears emphasizing:

.. warning::
    Don't mix traditional fixtures with class-based fixtures unless you have a
    compelling reason to do so. If you do, be careful. Django-class-fixtures
    can handle dependencies inside a single fixture module, but you need to
    manually ensure that Django-style serialized fixtures are **always**
    loaded before the class-based fixture modules that relate to objects
    contained therein.
    
    The same goes for dependencies between class-based fixture modules.
    django-class-fixtures doesn't currently support inter-module dependencies.
    If, through relation dependencies, you make assumptions about the loading
    order of the fixture modules, be very careful to actually load them in the
    correct order, always, without fail.

That concludes our coverage of the basic concepts and use of class-based
fixtures. You're not done yet, though. Next, it's recommended you look at
:doc:`using` for a brief look at actually using the fixture modules in
various scenarios.

For information on topics like using natural keys to create relations,
more in-depth technical details and a few gotchas, see :doc:`moreinfo`.
