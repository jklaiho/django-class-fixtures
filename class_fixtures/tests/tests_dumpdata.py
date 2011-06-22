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
