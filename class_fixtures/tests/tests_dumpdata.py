import re
from django.core.management import call_command
from django.test import TestCase

from class_fixtures.tests.models import (Band, Musician,
    Membership, Roadie, Competency, JobPosting, ComprehensiveModel)
from class_fixtures.utils import string_stdout

class DumpDataTests(TestCase):
    def test_encoding_declaration(self):
        with string_stdout() as output:
            call_command('dumpdata', 'tests', format='class')
            self.assertTrue(output.getvalue().startswith('# -*- coding: utf-8 -*-\n'))

    def test_correct_imports_in_output(self):
        band = Band.objects.create(name="Brutallica")
        musician = Musician.objects.create(name="Lars Toorich")
        membership = Membership.objects.create(band=band, musician=musician, instrument="Bongos", date_joined="1982-01-01")
        roadie = Roadie.objects.create(name="Ciggy Tardust")
        roadie.hauls_for.add(band)
        with string_stdout() as output:
            call_command('dumpdata', 'tests', format='class', exclude=[
                'tests.Party', 'tests.Politician'])
            lines = output.getvalue().split('\n')
            fixture_import, model_imports = lines[1], lines[2]
            self.assertEqual(fixture_import, "from class_fixtures.models import Fixture")
            self.assertEqual(model_imports, "from tests.models import Band, Membership, Musician, Roadie")

    def test_correct_fixtures_in_output(self):
        band = Band.objects.create(name="Brutallica")
        musician = Musician.objects.create(name="Lars Toorich")
        membership = Membership.objects.create(band=band, musician=musician, instrument="Bongos", date_joined="1982-01-01")
        roadie = Roadie.objects.create(name="Ciggy Tardust")
        roadie.hauls_for.add(band)
        with string_stdout() as output:
            call_command('dumpdata', 'tests', format='class', exclude=[
                'tests.Party', 'tests.Politician'])
            lines = output.getvalue().split('\n')
            self.assertEqual(lines[4], 'tests_band_fixture = Fixture(Band)')
            self.assertEqual(lines[5], 'tests_musician_fixture = Fixture(Musician)')
            self.assertEqual(lines[6], 'tests_membership_fixture = Fixture(Membership)')
            self.assertEqual(lines[7], 'tests_roadie_fixture = Fixture(Roadie)')

    def test_correct_fixture_populating(self):
        band = Band.objects.create(name="Brutallica")
        musician = Musician.objects.create(name="Lars Toorich")
        membership = Membership.objects.create(band=band, musician=musician, instrument="Bongos", date_joined="1982-01-01")
        roadie = Roadie.objects.create(name="Ciggy Tardust")
        roadie.hauls_for.add(band)
        with string_stdout() as output:
            call_command('dumpdata', 'tests', format='class', exclude=[
                'tests.Party', 'tests.Politician'])
            lines = output.getvalue().split('\n')
            self.assertEqual(lines[9], "tests_band_fixture.add(1, **{'name': u'Brutallica'})")
            self.assertEqual(lines[10], "tests_musician_fixture.add(1, **{'name': u'Lars Toorich'})")
            self.assertEqual(lines[11], "tests_membership_fixture.add(1, **{'band': 1, 'date_joined': datetime.date(1982, 1, 1), 'instrument': u'Bongos', 'musician': 1})")
            self.assertEqual(lines[12], "tests_roadie_fixture.add(1, **{'hauls_for': [1], 'name': u'Ciggy Tardust'})")

    def test_escaped_characters_in_strings(self):
        band = Band.objects.create(name="The Apostrophe's Apostles")
        musician = Musician.objects.create(name="Ivan \"The Terrible\" Terrible")
        musician2 = Musician.objects.create(name="\\, aka the artist formerly known as Backslash")
        membership = Membership.objects.create(band=band, musician=musician, instrument="Bass", date_joined="2000-12-05")
        membership = Membership.objects.create(band=band, musician=musician2, instrument="Guitar", date_joined="2000-12-05")
        roadie = Roadie.objects.create(name='Simon \'Single Quote\' DeForestation')
        roadie.hauls_for.add(band)
        with string_stdout() as output:
            call_command('dumpdata', 'tests', format='class', exclude=[
                'tests.Party', 'tests.Politician'])
            lines = output.getvalue().split('\n')
            self.assertEqual(lines[9], """tests_band_fixture.add(1, **{'name': u"The Apostrophe's Apostles"})""")
            self.assertEqual(lines[10], """tests_musician_fixture.add(1, **{'name': u'Ivan "The Terrible" Terrible'})""")
            # Raw string to represent what's actually printed out, would be four backslashes without it
            self.assertEqual(lines[11], r"""tests_musician_fixture.add(2, **{'name': u'\\, aka the artist formerly known as Backslash'})""")
            self.assertEqual(lines[12], """tests_membership_fixture.add(1, **{'band': 1, 'date_joined': datetime.date(2000, 12, 5), 'instrument': u'Bass', 'musician': 1})""")
            self.assertEqual(lines[13], """tests_membership_fixture.add(2, **{'band': 1, 'date_joined': datetime.date(2000, 12, 5), 'instrument': u'Guitar', 'musician': 2})""")
            self.assertEqual(lines[14], """tests_roadie_fixture.add(1, **{'hauls_for': [1], 'name': u"Simon 'Single Quote' DeForestation"})""")

    def test_complex_model(self):
        import datetime
        from decimal import Decimal

        # https://docs.djangoproject.com/en/dev/ref/models/fields/#bigintegerfield
        bigintfield_max = 9223372036854775807
        cm = ComprehensiveModel.objects.create(
            bigint = bigintfield_max,
            boolean = True,
            char = 'Hey hey now',
            date = datetime.date(2011, 6, 6),
            datetime = datetime.datetime(2011, 5, 5, 12, 30, 7),
            decimal = Decimal('1234.56'),
            floatf = 2345.67,
            integer = 345678,
            nullboolean = None,
            time = datetime.time(14, 45, 30),
            text = "Bacon ipsum dolor sit amet ham eiusmod cupidatat, "
"hamburger voluptate non dolor. Pork belly excepteur chuck, shankle ullamco "
"fugiat meatloaf est quis meatball sint dolore. Shank drumstick sint, tri-tip "
"deserunt proident in. Pancetta laboris culpa beef, pork chop venison magna "
"duis tail. Nulla in sirloin, minim bresaola ham cupidatat drumstick spare ribs "
"eiusmod ut. Shankle mollit ut, short ribs pork chop drumstick meatloaf duis "
"""elit reprehenderit. Cillum short loin flank est beef.

And the second paragraph looks like this.""")

        with string_stdout() as output:
            call_command('dumpdata', 'tests', format='class', exclude=[
                'tests.Party', 'tests.Politician'])
            lines = output.getvalue().split('\n')

        self.assertEqual(lines[2], "from tests.models import ComprehensiveModel")
        self.assertEqual(lines[4], "tests_comprehensivemodel_fixture = Fixture(ComprehensiveModel)")

        # Write-only code that turns the dumpdata output into a dictionary of
        # keys and values to be tested individually
        model_fields = dict([(j[0].strip("'"), j[1].strip(" ")) for j in
            [i.split(':') for i in re.split(", '|\{|\}\)", lines[6]) if ':' in i]
        ])

        # Depending on the platform where the test is being run, bigintfield_max
        # may be an integer or a long, depending on the value of sys.maxint.
        # The repr() result on the field will vary accordingly (L suffix or not),
        # so assertEqual instead repr()'s the value (like the serializer does)
        # because we can't have a single string representation for the value
        # that would work across all platforms.
        #
        # There's one more complication: on some systems, Python sees the
        # bigintfield_max value as an integer, but after it comes back from the
        # database, it is transformed into a long, presumably due to the SQLite
        # configuration. So, we retrieve the object from the database and repr()
        # its bigint field instead of the original value.
        db_cm = ComprehensiveModel.objects.get(pk=cm.pk)

        self.assertEqual(model_fields['bigint'], repr(db_cm.bigint))
        self.assertEqual(model_fields['boolean'], 'True')
        self.assertEqual(model_fields['char'], "u'Hey hey now'")
        self.assertEqual(model_fields['date'], 'datetime.date(2011, 6, 6)')
        self.assertEqual(model_fields['datetime'], 'datetime.datetime(2011, 5, 5, 12, 30, 7)')
        self.assertEqual(model_fields['decimal'], "Decimal('1234.56')")
        # Float representations are tricky prior to Python 2.7, hopefully this
        # is a good enough test for correctness of repr(2345.67) there
        self.assertRegexpMatches(model_fields['floatf'], '^2345.6(70*|69*)$')
        self.assertEqual(model_fields['integer'], '345678')
        self.assertEqual(model_fields['nullboolean'], 'None')
        self.assertEqual(model_fields['time'], 'datetime.time(14, 45, 30)')
        self.assertEqual(model_fields['text'], "u'Bacon ipsum dolor sit amet ham eiusmod cupidatat, "
            "hamburger voluptate non dolor. Pork belly excepteur chuck, shankle ullamco fugiat meatloaf "
            "est quis meatball sint dolore. Shank drumstick sint, tri-tip deserunt proident in. Pancetta "
            "laboris culpa beef, pork chop venison magna duis tail. Nulla in sirloin, minim bresaola ham "
            "cupidatat drumstick spare ribs eiusmod ut. Shankle mollit ut, short ribs pork chop drumstick "
            "meatloaf duis elit reprehenderit. Cillum short loin flank est beef.\\n\\n"
            "And the second paragraph looks like this.'")

    def test_natural_key_output(self):
        rails_n00b = Competency.objects.create(framework='Ruby on Rails', level=1)
        cake_adept = Competency.objects.create(framework='CakePHP', level=2)
        spring_master = Competency.objects.create(framework='Spring', level=3)
        django_guru = Competency.objects.create(framework='Django', level=4)

        rails_job = JobPosting.objects.create(title='Rails Intern', main_competency=rails_n00b)
        django_job = JobPosting.objects.create(title='Elder Django Deity', main_competency=django_guru)
        misc_job = JobPosting.objects.create(title='A man of many talents', main_competency=spring_master)

        django_job.additional_competencies.add(rails_n00b)
        misc_job.additional_competencies.add(cake_adept, rails_n00b)
        with string_stdout() as output:
            call_command('dumpdata', 'tests', format='class', exclude=[
                'tests.Party', 'tests.Politician'])
            lines = output.getvalue().split('\n')
            self.assertEqual(lines[2], "from tests.models import Competency, JobPosting")
            self.assertEqual(lines[4], "tests_competency_fixture = Fixture(Competency)")
            self.assertEqual(lines[5], "tests_jobposting_fixture = Fixture(JobPosting)")
            self.assertEqual(lines[7], "tests_competency_fixture.add(1, **{'framework': u'Ruby on Rails', 'level': 1})")
            self.assertEqual(lines[8], "tests_competency_fixture.add(2, **{'framework': u'CakePHP', 'level': 2})")
            self.assertEqual(lines[9], "tests_competency_fixture.add(3, **{'framework': u'Spring', 'level': 3})")
            self.assertEqual(lines[10], "tests_competency_fixture.add(4, **{'framework': u'Django', 'level': 4})")
            self.assertEqual(lines[11], "tests_jobposting_fixture.add(1, **{'additional_competencies': [], 'main_competency': 1, 'title': u'Rails Intern'})")
            self.assertEqual(lines[12], "tests_jobposting_fixture.add(2, **{'additional_competencies': [1], 'main_competency': 4, 'title': u'Elder Django Deity'})")
            self.assertEqual(lines[13], "tests_jobposting_fixture.add(3, **{'additional_competencies': [1, 2], 'main_competency': 3, 'title': u'A man of many talents'})")
