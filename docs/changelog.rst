Changelog and Roadmap
=====================

.. _past:

Past releases
-------------

0.8
###

* Initial public release. ``loaddata`` support only for class-based fixtures,
  the necessary ``dumpdata`` override not yet implemented.

.. _future:

Planned future releases
-----------------------

Here's a feature roadmap for the foreseeable future. In case updates that
break something are made to Django prior to 1.0, 0.x.y versions may be
released. Otherwise, "micro" versions will only be released for post-1.0
bugfix releases. Prior to that, bugfixes will exist in development code only.

0.9
###

* Fix any issues discovered in the initial release.
* Implement a ``dumpdata`` override for serializing Django models into
  :class:`Fixture` instances. You'll still have to manually direct the 
  ``dumpdata`` output into .py files, same as now with, say, .json files. The
  output will try to be complete, including all necessary model imports, so
  that you don't need to modify the generated code by hand.
  
  .. note::
    I know, "generated code" has a bad ring to it for Django users who know
    their history. However, the code inside fixture modules is so simple
    structurally that I'm confident the generating can be done reliably.
    
* Add proper class and exception documentation.
* Possibly: a helper method that formalizes the technique described in
  :ref:`structureddata`.
* Possibly: integration with `milkman <http://pypi.python.org/pypi/milkman>`_.
  You'd be able to easily use ``TestCase.fixtures`` in your tests while still
  making good use of the randomly generated model instances, consolidating the
  creation of both random and predefined models in your fixture modules. The
  syntax could be something like::
  
      bands = Fixture(Band)
      musicians = Fixture(Musician)
      # You need the band to have specific non-random attributes
      bands.add(1, name="Arcade Water", genre="Indie")
      # You don't care about the details of the musicians, apart from them
      # being a part of a certain band; all other information is generated.
      musicians.add_random(member_of=[1])
      musicians.add_random(member_of=[1])
  
  ``add_random`` would be available if *milkman* was on your Python path.
  
  I haven't yet used *milkman* myself, and I don't know if this feature would be all that
  useful, but I thought I'd mention it here just in case someone thinks this
  would be great. If you do, let me know about it.
* Possibly: conditional loading of :class:`Fixture` instances. Through some (I
  hope) elegant mechanism, allow individual :class:`Fixture` instances to be
  able to determine whether some arbitrary prerequisites are met prior to
  being loaded. If they are not, either fail silently and keep going, or abort
  and raise an exception (depending on some parameter).
  
  This is different from what's described in :ref:`dynamicfixtures`, where the
  already possible methods of conditionally instantiating and populating
  :class:`Fixture` instances are discussed. As of 0.8, there's no official way
  to conditionally prevent the loading process itself.
  
  This is just an idea at this stage, I'll need to come up with compelling use
  cases before putting in the work. Also, this may get a bit hairy with
  inter-fixture dependencies, at least in the "fail silently" case.

1.0
###

* The first version that can be recommended for use in production.
* Availability on PyPi.
* No new features are planned yet. The idea is to promote a post-0.9 trunk
  version to 1.0 once sufficient real-world testing has taken place and any
  issues discovered in 0.9 have been ironed out. Followed by bugfix/Django
  compatibility releases (micro versions) or small feature releases (minor
  versions) in perpetuity, or until...

2.0
###

* ...which is purely hypothetical at this point and may never actually see the
  light of day.
* Pipe dream: some type of integration with schema migrations, namely South or
  whatever may appear in Django core. This could take the form of having
  ``Fixture`` instantation happen against a specific generation of the model
  class (as frozen by the migration machinery) that is schema-compatible with
  the assumptions of the fixture (i.e. whatever schema was in place when the
  fixture was first created).
  
  Utterly fictional examples of ``dumpdata`` output after creating the
  fixture, with "0003_add_some_fields" being the latest migration applied that
  contains changes to the Band model::
    
    # With automatic lookup for the migration module
    bands = Fixture(Band, rev='0003_add_neat_fields')
    
    # With explicit import of a South-frozen model dictionary from
    # a migration module:
    from someapp.migrations.0003_add_neat_fields import models as m_0003
    bands = Fixture(m_0003['bandaid.Band'])
    
    bands.add(1, **stuff_as_of_0003)
    
  ...or something like that.
  
  Later on, you change the schema of ``Band`` and create new migrations,
  making the fixture module outdated. ``loaddata`` would notice this, and
  there would be an automated mechanism in place to apply all
  post-fixture-creation migrations to all ``Band`` fixtures in the fixture
  module to modernize the schema of their contained objects before creating
  them. You would then get fresh ``dumpdata`` output with the modern schema,
  with which you would replace the old code in the fixture module. It could
  look like this, following the previous theoretical syntaxes::
  
    bands = Fixture(Band, rev='0008_rename_this_to_that')
    
    # or
    
    from someapp.migrations.0008_rename_this_to_that import models as m_0008
    bands = Fixture(m_0008['bandaid.Band'])
    
    bands.add(1, **stuff_as_of_0008)
  
  You get the picture.
  
  This feature would rock so hard it's uncanny. No more manual updating of
  fixtures due to schema changes and migrations (save for piping the fresh
  ``dumpdata`` output into a .py file). Unfortunately, there are tons of open
  questions and hard problems here. This option hasn't yet been researched for
  any sort of feasibility at all. I'm mentioning it here just in case some
  enterprising Djangonaut is divinely inspired by the idea and decides to
  implement it. I'm not sure I'll ever have the skill or patience for it.
