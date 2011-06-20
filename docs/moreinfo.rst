Additional Information
======================

Here's some slightly more advanced information that you may find useful.

.. _naturalkeys:

Natural keys
------------

First of all, read and understand `Django's natural key documentation`_.

.. _Django's natural key documentation: https://docs.djangoproject.com/en/dev/topics/serialization/#natural-keys

Since version 0.8 of django-class-fixtures only supports ``loaddata`` but not
``dumpdata``, we'll focus on the loading side of things.

To demonstrate natural keys, we'll use the following two models,
``Competency`` being the one with the custom manager required for natural
key loading::

    class CompetencyManager(models.Manager):
        def get_by_natural_key(self, framework, level):
            return self.get(framework=framework, level=level)

    class Competency(models.Model):
        LEVEL_CHOICES = (
            (0, "None"),
            (1, "Beginner"),
            (2, "Intermediate"),
            (3, "Advanced"),
            (4, "Guru"),
        )
        framework = models.CharField(max_length=100)
        level = models.SmallIntegerField(choices=LEVEL_CHOICES)

        objects = CompetencyManager()

        class Meta(object):
            unique_together = (('framework', 'level'))
    
    
    class JobPosting(models.Model):
        title = models.CharField(max_length=100)
        main_competency = models.ForeignKey(Competency, related_name='main_competency_for')
        additional_competencies = models.ManyToManyField(Competency, related_name='extra_competency_for')

Natural keys are meant to be used when relating from a fixture to an object
that is already in the database, where defining the relation based on the
target object's primary key is inconvenient or even impossible.

To demonstrate, we create a few ``Competency`` objects beforehand in a
``manage.py shell`` session::

    rails_n00b = Competency.objects.create(framework='Ruby on Rails', level=1)
    cake_adept = Competency.objects.create(framework='CakePHP', level=2)
    spring_master = Competency.objects.create(framework='Spring', level=3)
    django_guru = Competency.objects.create(framework='Django', level=4)

Instead of referring to those objects using primary keys (which we'd have to
look up), we'd much rather just use a ``(framework, level)`` natural key
tuple, since pairs of those will uniquely identify ``Competency`` objects in
the database.

Here are the various ways of doing natural key relations from ``JobPosting``
fixtures to those pre-existing ``Competency`` objects::

    jobs = Fixture(JobPosting)
    
    # A single foreign key with a natural key tuple
    jobs.add(1, title='Rails Intern', main_competency=('Ruby on Rails', 1))
    
    # One FK, and a single M2M with a natural key tuple in a single-item list
    jobs.add(2, title='Elder Django Deity', main_competency=('Django', 4),
        additional_competencies=[('Ruby on Rails', 1)])
    
    # One FK, and several M2Ms with a list of multiple natural key tuples
    jobs.add(3, title='A man of many talents', main_competency=('Spring', 3), 
        additional_competencies=[('CakePHP', 2), ('Ruby on Rails', 1)]
    )

As with normal primary key-based relations, foreign keys accept a single
natural key tuple, whereas many-to-many fields require an iterable of them,
even with a single item.

.. _rawmode:

Raw mode
--------

When Django deserializes fixtures, it doesn't actually call the :func:`save`
method of the respective model classes directly. Instead, it uses
``DeserializedObject``, a container class for pre-saved deserialized data,
found in ``django.core.serializers.base``. Here's the relevant bit from its
:func:`save` method (as of Django 1.3)::

    # Call save on the Model baseclass directly. This bypasses any
    # model-defined save. The save is also forced to be raw.
    # This ensures that the data that is deserialized is literally
    # what came from the file, not post-processed by pre_save/save
    # methods.
    models.Model.save_base(self.object, using=using, raw=True)

The comment probably doesn't need further explanation. :class:`Fixture`, on
the other hand, has an optional boolean ``raw`` parameter that defaults to
``False``, meaning that in django-class-fixtures, saves are done in "normal"
mode by default, using the :func:`create` method of the default manager of the
actual model class.

Remember the *wage_slave* app from the introduction? Let's revisit it, adding
some custom :func:`save` logic to demonstrate the use and effects of raw
mode::

    class Company(models.Model):
        name = models.CharField(max_length=100)

    class Employee(models.Model):
        name = models.CharField(max_length=100)
        company = models.ForeignKey(Company)
        manager = models.ForeignKey('self', null=True)
        # New field, conditionally set to True in save()
        cog_in_the_machine = models.BooleanField(default=False)

        def save(self, *args, **kwargs):
            if ' corp' in self.company.name.lower():
                self.cog_in_the_machine = True
            super(Employee, self).save(*args, **kwargs)

The :func:`save` method of the :class:`Employee` class examines the employing
company, checking if its name contains something like "Corp." or
"Corporation". If it does, then in a rather silly bit of social commentary, it
deduces that this person is necessarily a dehumanized corporate drone, and
sets the ``cog_in_the_machine`` boolean to True.

Raw mode will prevent this, however. Here's what happens with fixtures set
to normal and raw mode::

    company_fixture = Fixture(Company)
    company_fixture.add(1, name='Bloatware Corporation')
    
    employee_fixture = Fixture(Employee)
    employee_fixture.add(1, name='Andy Depressant', company=company_fixture.fk(1), manager=None)
    raw_employee_fixture = Fixture(Employee, raw=True)
    raw_employee_fixture.add(2, name='Sadie Peon', company=company_fixture.fk(1), manager=None)

Once a fixture module containing those fixtures is loaded, we can check to see
that in raw mode, Sadie was spared the humiliation::
    
    >>> andy = Employee.objects.get(pk=1)
    >>> sadie = Employee.objects.get(pk=2)
    >>> andy.cog_in_the_machine
    True
    >>> sadie.cog_in_the_machine
    False

Raw mode in django-class-fixtures is a feature I'd appreciate testing and
feedback on. I'm not entirely sure about all the implications of it being set
to either ``True`` or ``False``; it just felt natural to leave it to False
when dealing with Python code instead of, say, a JSON serialization.

If you run into use cases where ``raw=True`` is necessary, I'd be glad to hear
about them. If you have a compelling argument why raw mode should be on by
default, do tell. It's possible that when I get to work implementing a
``dumpdata`` override for 0.9, I'll set ``raw=True`` for all fixtures
created programmatically with ``dumpdata``, or even change the default
mode, if testing produces results to support that action.

.. _multidb:

Multiple database support
-------------------------

I've tried to be diligent in making all of the database operations in
django-class-fixtures work cleanly with multiple databases, and there are
even a couple of tests for it, but I have no experience actually using
Django's multiple database support in real-world environments.

Also, check out the note in :ref:`loaddataoutput` below for a possible minor
caveat associated with custom database routers.

I'd appreciate more testing of this for feature parity with Django's fixture
system.

.. _loadingrules:

Rules for fixture discovery and loading
---------------------------------------

The various forms of specifying fixtures for loading are detailed in
:ref:`this example <testcasefixtures>` of ``TestCase.fixtures``. Options 1 and
2 there are always handled by django-class-fixtures alone, but the strings in
options 3, 4 and 5 are all valid monikers for Django fixtures, too, so there's
some logic in place to determine who handles what.

The ``loaddata`` override looks at each fixture name it's given, and
internally assigns either Django or django-class-fixtures to handle each,
sometimes both. Some shadowing related to app names also takes place that may
bite you in the ass if you're not careful. Here's a look at what happens with
various types of strings:

**File names with registered fixture extensions** such as
``"example_band.json"`` are assigned to be handled directly by Django's
``loaddata``, no questions asked. If you've written a custom serializer that
uses some other format and extension than those provided by Django, the same
applies for file names matching those. The "reserved" extensions are sourced
from Django's serialization machinery, where custom stuff is also registered.

**Strings with dots** such as ``"other.thing"`` or ``"bandaid.other_bands"``
are split on the dots, and the first element of the resulting list is matched
against the names of all installed apps. Of those two, ``other`` does not
correspond to an app, so the whole string is passed on to be handled by
Django's ``loaddata``, matching files like ``"other.thing.json"``.

``bandaid`` is an installed app, however, so a fixture module called
``other_bands`` is searched for under the its ``fixtures`` subpackage. If
found, it alone gets loaded and any further searches are not made on that
name. If not found, a :exc:`FixtureUsageError` exception is raised.

.. note::
    Raising an exception may seem harsh, when one could just pass the string
    on for Django to handle, but I wanted to make references to
    ``appname.module_name`` clearly distinct from other string forms to avoid
    cases where they would get passed on to Django due to a typo in the module
    name, and then silently ignored when files matching the name are not
    found, since Django does not raise errors in case of non-existent
    fixtures.

This means that any traditional fixture files that start with an app name
followed by a dot, like ``bandaid.anythingatall.json`` are shadowed and not
loaded, if referred to as ``"bandaid.anythingatall"``. The solution is to
always include the file extension in cases like these, triggering the
automatic assignment for Django's ``loaddata`` as described above.

**Arbitrary strings with no dots** such as ``"something"`` are first checked
against app names. If a match is found, no further determination takes place.
All the fixture modules (but no traditional fixtures) of that app are loaded.
This shadows both ``"something.json"`` files and fixture modules called
``"something.py"``, so don't name your traditional fixtures or fixture modules
the same as any apps.

.. note::
    In this scenario, ``"something.json"`` is still accessible by referring to
    it with the .json extension and not just as ``"something"``. Remember:
    explicit is better than implicit.

If ``"something"`` isn't the name of an app, it is assigned for Django to
handle first. In addition, it is checked against the names of fixture modules
in all valid fixture module locations. All matches are marked for loading in
whatever order they are found (but always after Django has taken a crack at
locating and loading traditional fixture files with that name first).

That means you can have as many fixture modules called ``"something.py"`` in
as many ``fixtures`` directories or ``FIXTURE_PACKAGES`` locations as you
like. You can also have ``something.json`` and ``something.py`` under the same
directory/package, both will be loaded, Django first. No shadowing takes place
at this stage.

.. _loaddataoutput:

Differences in the output of ``loaddata``
-----------------------------------------

Due to the process described above in :ref:`loadingrules`, when
django-class-fixtures needs to fall back to Django's ``loaddata``, it does so
for a single fixture name parameter at a time. That is, if the parameters to
``loaddata`` include ``"something.json"`` and ``"other_thing.json"``, that
results in two runs of Django's ``loaddata``, not one for both together. This
is to ensure that the user-specified fixture ordering is preserved when mixing
traditional and class-based fixtures; it won't do to just pick out all the
traditional fixtures from the list and give them to the original ``loaddata``
command in one bunch.

The outputs from those two runs are stored and parsed for the loaded fixture
counts. Those counts are then combined with the counts produced by any
class-based fixtures.

Any extra messages produced by calls to Django's ``loaddata`` when verbosity
is 2 or 3 are stored and displayed in order of appearance. This is followed by
the summary row (shown as the only row with a verbosity of 1, too), which is
either "No fixtures found." or "Installed **x** object(s) from **y**
fixture(s)" to match what Django outputs.

.. note::
    Django actually has a third form of the summary row: "Installed **x**
    object(s) (of **z**) from **y** fixture(s)." As far as I can tell by
    looking at the code of Django's ``loaddata``, this comes into play when
    using multiple databases and a custom database router disallows the
    loading of instances of a certain model into a certain database.
    
    As of 0.8, the **x** and **y** counts are parsed from that and correctly
    included in the final count, but the ``loaddata`` override's summary row
    does not parse or include the "(of **z**)" bit. I was too lazy to
    implement it, frankly. If you rely on it, patches are welcome, or you can
    hope that I find the motivation to implement it in a later version.

If you use scripts that rely on the precise output of ``loaddata`` (as part of
`Fabric`_ deployments, for example), be sure to test them thoroughly. This is
another area I'm happy to receive feedback about, there may be arguments for
changing some aspect of django-class-fixtures' behaviour.

.. _Fabric: http://fabfile.org/
