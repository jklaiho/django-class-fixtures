from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from class_fixtures.management.commands.dumpdata import Command as Dumpdata
from class_fixtures.tests.models import (Band, MetalBand, Musician,
    Membership, Roadie, Company, Employee, EmployeeHistory, Competency,
    JobPosting, Party, Politician)
from class_fixtures.utils import string_stdout

class BasicDumpingFunctionalityTests(TestCase):
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
        # TODO
        pass
