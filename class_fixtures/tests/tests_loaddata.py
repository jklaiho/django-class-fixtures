import os
import sys

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.utils.importlib import import_module

from class_fixtures.exceptions import RelatedObjectError, FixtureUsageError
from class_fixtures.management.commands.loaddata import Command as Loaddata
from class_fixtures.models import Fixture
from class_fixtures.tests.models import (Band, MetalBand, Musician,
    Membership, Roadie, Company, Employee, EmployeeHistory, Competency,
    JobPosting, Party, Politician)
from class_fixtures.utils.loaddata import (associate_handlers,
    process_django_output)
from class_fixtures.utils import string_stdout

class LoaddataOverrideTest(TestCase):
    def test_overriding(self):
        """
        Confirm that the custom loaddata command is being used when
        class_fixtures is in INSTALLED_APPS. This is a safeguard for having
        multiple loaddata-overriding apps in a Django project, with
        django-class-fixtures not being the one whose loaddata gets used.
        
        Strictly speaking this is an initialization check rather than a test
        of functionality, but checking for this at startup is a bit fragile
        (with regards to what gets loaded by Django in which order). When
        running tests for a Django project with multiple apps, all the apps
        are in place and the correct loaddata override can be verified.
        """
        from django.core.management import _commands
        
        if 'class_fixtures' in settings.INSTALLED_APPS:
            self.assertEqual(_commands['loaddata'], 'class_fixtures',
                """class_fixtures is in INSTALLED_APPS, but its loaddata
                override is not active. The current loaddata command is
                provided by '%s'. Another app that overrides loaddata cannot
                be active at the same time as django-class-fixtures.""" % _commands['loaddata']
            )


class BasicLoadingFunctionalityTests(TestCase):
    def test_simple_fixture(self):
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses")
        band_fixture.load()
        self.assertEqual(Band.objects.count(), 1)
    
    def test_empty_fixture(self):
        # Since we allow dynamic populating of Fixture instances, loading
        # empty ones should not produce an error (unlike Django, where empty
        # fixture files will do that).
        band_fixture = Fixture(Band)
        band_fixture.load()
        self.assertEqual(Band.objects.count(), 0)
    
    def test_fk_relation(self):
        company_fixture = Fixture(Company)
        company_fixture.add(1, name='Macrohard')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=company_fixture.fk(1), manager=None)
        company_fixture.load()
        employee_fixture.load()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 1)
        self.assertTrue(Employee.objects.all()[0].company == Company.objects.all()[0])
    
    def test_single_m2m_relation(self):
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses")
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[band_fixture.m2m(1)])
        band_fixture.load()
        roadie_fixture.load()
        self.assertEqual(Band.objects.count(), 1)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.filter(name="Nuns N' Hoses").count(), 1)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.filter(name='Marshall Amp').count(), 1)
    
    def test_reverse_single_m2m_relation(self):
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp')
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses", roadie_set=[roadie_fixture.m2m(1)])
        roadie_fixture.load()
        band_fixture.load()
        self.assertEqual(Band.objects.count(), 1)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.filter(name="Nuns N' Hoses").count(), 1)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.filter(name='Marshall Amp').count(), 1)
    
    def test_multiple_m2m_relations(self):
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses")
        band_fixture.add(2, name='Led Dirigible')
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[band_fixture.m2m(1), band_fixture.m2m(2)])
        band_fixture.load()
        roadie_fixture.load()
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.count(), 2)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.count(), 1)
        self.assertEqual(Band.objects.get(name='Led Dirigible').roadie_set.count(), 1)
    
    def test_reverse_multiple_m2m_relations(self):
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp')
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses", roadie_set=[roadie_fixture.m2m(1)])
        band_fixture.add(2, name='Led Dirigible', roadie_set=[roadie_fixture.m2m(1)])
        band_fixture.load()
        roadie_fixture.load()
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.count(), 2)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.count(), 1)
        self.assertEqual(Band.objects.get(name='Led Dirigible').roadie_set.count(), 1)
    
    def test_o2o_relation(self):
        company_fixture = Fixture(Company)
        company_fixture.add(1, name='Macrohard')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=company_fixture.fk(1), manager=None)
        history_fixture = Fixture(EmployeeHistory)
        history_fixture.add(1, employee=employee_fixture.o2o(1), date_joined='2007-02-22')
        company_fixture.load()
        employee_fixture.load()
        history_fixture.load()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(EmployeeHistory.objects.count(), 1)
        self.assertEqual(Employee.objects.all()[0].employeehistory, EmployeeHistory.objects.all()[0])
    
    def test_fk_to_preexisting_object(self):
        company = Company.objects.create(name='Macrohard')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=company, manager=None)
        employee_fixture.load()
        self.assertEqual(Employee.objects.count(), 1)
        self.assertTrue(Employee.objects.all()[0].company == company)
    
    def test_fk_to_pk_value(self):
        company = Company.objects.create(name='Macrohard')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=1, manager=None)
        employee_fixture.load()
        self.assertEqual(Employee.objects.count(), 1)
        self.assertTrue(Employee.objects.all()[0].company == company)
    
    def test_single_m2m_to_preexisting_object(self):
        band = Band.objects.create(name="Nuns N' Hoses")
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[band])
        roadie_fixture.load()
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.filter(name="Nuns N' Hoses").count(), 1)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.filter(name='Marshall Amp').count(), 1)
    
    def test_single_m2m_to_pk_value(self):
        band = Band.objects.create(pk=1, name="Nuns N' Hoses")
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[1])
        roadie_fixture.load()
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.filter(name="Nuns N' Hoses").count(), 1)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.filter(name='Marshall Amp').count(), 1)
    
    def test_multiple_m2ms_to_preexisting_objects(self):
        band1 = Band.objects.create(name="Nuns N' Hoses")
        band2 = Band.objects.create(name='Led Dirigible')
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[band1, band2])
        roadie_fixture.load()
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.count(), 2)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.count(), 1)
        self.assertEqual(Band.objects.get(name='Led Dirigible').roadie_set.count(), 1)
    
    def test_multiple_m2ms_to_pk_values(self):
        band1 = Band.objects.create(pk=1, name="Nuns N' Hoses")
        band2 = Band.objects.create(pk=2, name='Led Dirigible')
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[1, 2])
        roadie_fixture.load()
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.count(), 2)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.count(), 1)
        self.assertEqual(Band.objects.get(name='Led Dirigible').roadie_set.count(), 1)
    
    def test_multiple_m2ms_to_mixed_fixture_pk_preexisting(self):
        band1 = Band.objects.create(pk=1, name="Nuns N' Hoses")
        band2_fixture = Fixture(Band)
        band2_fixture.add(2, name='Led Dirigible')
        band3 = Band.objects.create(pk=3, name='Bar Fighters')
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[band1, band2_fixture.fk(2), 3])
        roadie_fixture.load()
        self.assertEqual(Band.objects.count(), 3)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.count(), 3)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.count(), 1)
        self.assertEqual(Band.objects.get(name='Led Dirigible').roadie_set.count(), 1)
        self.assertEqual(Band.objects.get(name='Bar Fighters').roadie_set.count(), 1)
    
    def test_o2o_to_pk_value(self):
        company = Company.objects.create(pk=1, name='Macrohard')
        employee = Employee.objects.create(pk=1, name='Andy Depressant', company=company, manager=None)
        history_fixture = Fixture(EmployeeHistory)
        history_fixture.add(1, employee=1, date_joined='2007-02-22')
        history_fixture.load()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(EmployeeHistory.objects.count(), 1)
        self.assertEqual(Employee.objects.all()[0].employeehistory, EmployeeHistory.objects.all()[0])
    
    def test_o2o_to_preexisting_object(self):
        company = Company.objects.create(pk=1, name='Macrohard')
        employee = Employee.objects.create(pk=1, name='Andy Depressant', company=company, manager=None)
        history_fixture = Fixture(EmployeeHistory)
        history_fixture.add(1, employee=employee, date_joined='2007-02-22')
        history_fixture.load()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(EmployeeHistory.objects.count(), 1)
        self.assertEqual(Employee.objects.all()[0].employeehistory, EmployeeHistory.objects.all()[0])
    
    def test_natural_keys_to_preexisting_objects(self):
        rails_n00b = Competency.objects.create(framework='Ruby on Rails', level=1)
        cake_adept = Competency.objects.create(framework='CakePHP', level=2)
        spring_master = Competency.objects.create(framework='Spring', level=3)
        django_guru = Competency.objects.create(framework='Django', level=4)
        
        jobs = Fixture(JobPosting)
        # No M2M
        jobs.add(1, title='Rails Intern', main_competency=('Ruby on Rails', 1))
        # Single M2M with a tuple in a single-item list
        jobs.add(2, title='Elder Django Deity', main_competency=('Django', 4),
            additional_competencies=[('Ruby on Rails', 1)])
        # Several M2Ms with a list of tuples
        jobs.add(3, title='A man of many talents', main_competency=('Spring', 3), 
            additional_competencies=[('CakePHP', 2), ('Ruby on Rails', 1)]
        )
        jobs.load()
        
        self.assertEqual(JobPosting.objects.count(), 3)
        no_m2m_job = JobPosting.objects.get(pk=1)
        self.assertEqual(no_m2m_job.main_competency, rails_n00b)
        single_m2m_job = JobPosting.objects.get(pk=2)
        self.assertEqual(single_m2m_job.additional_competencies.count(), 1)
        self.assertTrue(rails_n00b in single_m2m_job.additional_competencies.all())
        multi_m2m_job = JobPosting.objects.get(pk=3)
        self.assertEqual(multi_m2m_job.additional_competencies.count(), 2)
        self.assertTrue(all([c in multi_m2m_job.additional_competencies.all() for c in [cake_adept, rails_n00b]]))
    
    def test_raw_mode(self):
        company_fixture = Fixture(Company)
        company_fixture.add(1, name='Bloatware Corporation')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=company_fixture.fk(1), manager=None)
        # Due to raw=True, the custom save() method that sets
        # 'cog_in_the_machine' to True should not get run.
        raw_employee_fixture = Fixture(Employee, raw=True)
        raw_employee_fixture.add(2, name='Sadie Peon', company=company_fixture.fk(1), manager=None)
        company_fixture.load()
        employee_fixture.load()
        raw_employee_fixture.load()
        self.assertEqual(Employee.objects.count(), 2)
        normal = Employee.objects.get(name='Andy Depressant')
        raw = Employee.objects.get(name='Sadie Peon')
        self.assertEqual(normal.cog_in_the_machine, True)
        self.assertEqual(raw.cog_in_the_machine, False)


class DependencyResolutionTests(TestCase):
    """
    While Fixture instances in fixture modules need to be defined in the
    proper order due to their later use as relation targets with local
    variable references like ``some_fixture.fk(...)``, the order in which they
    are retrieved from that module and loaded is usually not the same as in
    which they were defined.
    
    This requires automatic dependency resolution. Dependencies are generated
    automatically when using the fk, m2m and o2o methods of fixture instances,
    and they need to be followed when running the load() method of instances
    that have these relations.
    """
    def test_one_level_fk_hierarchy(self):
        # FK from Employee to Company
        company_fixture = Fixture(Company)
        company_fixture.add(1, name='Macrohard')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=company_fixture.fk(1), manager=None)
        # Load in reverse order: 2nd, 1st level
        employee_fixture.load()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 1)
        # Should have gotten loaded
        self.assertTrue(company_fixture.loaded_to_db())
    
    def test_two_level_fk_o2o_hierarchy(self):
        # FK from Employee to Company, O2O from EmployeeHistory to Employee
        company_fixture = Fixture(Company)
        company_fixture.add(1, name='Macrohard')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=company_fixture.fk(1), manager=None)
        history_fixture = Fixture(EmployeeHistory)
        history_fixture.add(1, employee=employee_fixture.o2o(1), date_joined='2007-02-22')
        # Load in reverse order: 3rd, 2nd, 1st level
        history_fixture.load()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(EmployeeHistory.objects.count(), 1)
        # Should have gotten loaded
        self.assertTrue(employee_fixture.loaded_to_db())
        self.assertTrue(company_fixture.loaded_to_db())
    
    def test_two_level_fk_o2o_hierarchy_mixed(self):
        # FK from Employee to Company, O2O from EmployeeHistory to Employee
        company_fixture = Fixture(Company)
        company_fixture.add(1, name='Macrohard')
        employee_fixture = Fixture(Employee)
        employee_fixture.add(1, name='Andy Depressant', company=company_fixture.fk(1), manager=None)
        history_fixture = Fixture(EmployeeHistory)
        history_fixture.add(1, employee=employee_fixture.o2o(1), date_joined='2007-02-22')
        # Load in mixed order: 3rd, 1st, 2nd level
        history_fixture.load()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(EmployeeHistory.objects.count(), 1)
        # Should have gotten loaded
        self.assertTrue(company_fixture.loaded_to_db())
        self.assertTrue(employee_fixture.loaded_to_db())
    
    def test_m2m_dependent_first(self):
        # The above FK tests already apply to explicit "through" M2Ms, so this
        # only tests normal, "non-through" ones.
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses")
        band_fixture.add(2, name='Led Dirigible')
        roadie_fixture = Fixture(Roadie)
        roadie_fixture.add(1, name='Marshall Amp', hauls_for=[band_fixture.m2m(1), band_fixture.m2m(2)])
        # M2M relations are two-way, but like only one end has the
        # ManyToManyField, the fixture dependency is also defined in one end
        # of the relation. roadie_fixture is the dependent here, load it first
        # to test proper dependency resolution.
        roadie_fixture.load()
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Roadie.objects.get(name='Marshall Amp').hauls_for.count(), 2)
        self.assertEqual(Band.objects.get(name="Nuns N' Hoses").roadie_set.count(), 1)
        self.assertEqual(Band.objects.get(name='Led Dirigible').roadie_set.count(), 1)
        # Should have gotten loaded
        self.assertTrue(band_fixture.loaded_to_db())


class FixtureDiscoveryHandlingLoadingTests(TestCase):
    """
    Test the different ways of referring to class fixtures through
    ``TestCase.fixtures`` or ``manage.py loaddata``.
    
    ``fixtures = [fixture_instance]``
      Loads a single ``Fixture`` instance directly.
    
    ``fixtures = [fixture_module]``
      Loads all the ``Fixture`` instances contained in the referenced module.
    
    ``fixtures = ["appname"]`` or ``loaddata appname``
      The named app must have a ``fixtures`` package. All of the first-level
      descendant submodules of ``appname.fixtures`` are loaded, *except*
      ``appname.fixtures.initial_data``, which is only loaded through a 
      ``manage.py syncdb`` call.
    
    ``fixtures = ["appname.fixture_module"]`` or ``loaddata appname.fixture_module``
      Checks if there is a fixture module with the provided name under the
      ``fixtures`` package of the provided application, and loads all the
      fixtures contained there.
     
    ``fixtures = ["some_string"]`` or ``loaddata some_string``
      First, lets Django do its thing with the given string, in case
      traditional fixtures with that name are found.
      
      Second, looks for submodules with the given name under the ``fixtures``
      packages of all installed apps and all the packages listed in
      settings.FIXTURE_PACKAGES. All fixtures with that name are loaded in
      whatever order they are encountered.
      
      This syntax is the one used for loading initial data as well.
    """
    def test_fixture_instance(self):
        band_fixture = Fixture(Band)
        handlers = associate_handlers([band_fixture])
        self.assertEqual(handlers, [(band_fixture, 'class_fixtures', 'instance', None)])
    
    def test_fixture_module(self):
        fixture_module = import_module('class_fixtures.tests.fixtures.other_fixtures')
        handlers = associate_handlers([fixture_module])
        self.assertEqual(handlers, [(fixture_module, 'class_fixtures', 'module', None)])
        l = Loaddata()
        l.stdout = sys.stdout
        l.stderr = sys.stderr
        l.handle(fixture_module)
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(MetalBand.objects.count(), 1)
        self.assertEqual(Musician.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 2)
        self.assertEqual(Roadie.objects.count(), 3)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 2)
        self.assertEqual(EmployeeHistory.objects.count(), 2)
    
    def test_appname_string(self):
        handlers = associate_handlers(['tests'])
        fixture_package = import_module('class_fixtures.tests.fixtures')
        self.assertEqual(handlers, [('tests', 'class_fixtures', 'app_label', fixture_package)])
        l = Loaddata()
        l.stdout = sys.stdout
        l.stderr = sys.stderr
        l.handle('tests')
        # fixtures.some_fixtures and fixtures.other_fixtures contents combined
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(MetalBand.objects.count(), 1)
        self.assertEqual(Musician.objects.count(), 2)
        self.assertEqual(Roadie.objects.count(), 3)
        self.assertEqual(Membership.objects.count(), 2)
        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(Employee.objects.count(), 4)
        self.assertEqual(EmployeeHistory.objects.count(), 4)
    
    def test_appname_fixturemodule_string(self):
        handlers = associate_handlers(['tests.some_fixtures'])
        fixture_submodule = import_module('class_fixtures.tests.fixtures.some_fixtures')
        self.assertEqual(handlers, [('tests.some_fixtures', 'class_fixtures', 'submodule_name', fixture_submodule)])
        l = Loaddata()
        l.stdout = sys.stdout
        l.stderr = sys.stderr
        l.handle('tests.some_fixtures')
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 2)
        self.assertEqual(EmployeeHistory.objects.count(), 2)
    
    def test_fixture_module_string_1(self):
        handlers = associate_handlers(['some_fixtures'])
        fixture_submodule = import_module('class_fixtures.tests.fixtures.some_fixtures')
        self.assertEqual(handlers, [
            ('some_fixtures', 'django', None, None),
            ('some_fixtures', 'class_fixtures', 'submodule_name', fixture_submodule)
        ])
        l = Loaddata()
        l.stdout = sys.stdout
        l.stderr = sys.stderr
        l.handle('some_fixtures')
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 2)
        self.assertEqual(EmployeeHistory.objects.count(), 2)
        
    def test_fixture_module_string_2(self):
        handlers = associate_handlers(['app_level_fixture'])
        self.assertEqual(handlers, [('app_level_fixture', 'django', None, None)])
        l = Loaddata()
        l.stdout = sys.stdout
        l.stderr = sys.stderr
        l.handle('app_level_fixture', verbosity=0)
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(MetalBand.objects.count(), 1)
        self.assertEqual(Musician.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 3)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 2)
        self.assertEqual(EmployeeHistory.objects.count(), 2)
    
    def test_fixture_module_string_3(self):
        handlers = associate_handlers(['app_level_fixture.json'])
        self.assertEqual(handlers, [('app_level_fixture.json', 'django', None, None)])
        l = Loaddata()
        l.stdout = sys.stdout
        l.stderr = sys.stderr
        l.handle('app_level_fixture.json', verbosity=0)
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(MetalBand.objects.count(), 1)
        self.assertEqual(Musician.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 3)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 2)
        self.assertEqual(EmployeeHistory.objects.count(), 2)
    
    def test_fixture_module_string_4(self):
        # Loads tests/testproject/project_fixtures/project_level_fixture.json
        old_fixture_dirs = settings.FIXTURE_DIRS
        settings.FIXTURE_DIRS = (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testproject/project_fixtures'),)
        handlers = associate_handlers(['project_level_fixture'])
        self.assertEqual(handlers, [('project_level_fixture', 'django', None, None)])
        try:
            l = Loaddata()
            l.stdout = sys.stdout
            l.stderr = sys.stderr
            l.handle('project_level_fixture', verbosity=0)
        finally:
            settings.FIXTURE_DIRS = old_fixture_dirs
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(MetalBand.objects.count(), 1)
        self.assertEqual(Musician.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 3)
        self.assertEqual(Roadie.objects.count(), 1)
    
    def test_fixture_module_string_5(self):
        old_pkgs = getattr(settings, 'FIXTURE_PACKAGES', [])
        settings.FIXTURE_PACKAGES = [
            "class_fixtures.tests.some_fixture_modules",
        ]
        try:
            handlers = associate_handlers(['some_fixtures', 'moar_fixtures'])
            some_module = import_module('class_fixtures.tests.fixtures.some_fixtures')
            moar_module = import_module('class_fixtures.tests.some_fixture_modules.moar_fixtures')
            self.assertEqual(handlers, [
                ('some_fixtures', 'django', None, None),
                ('some_fixtures', 'class_fixtures', 'submodule_name', some_module),
                ('moar_fixtures', 'django', None, None),
                ('moar_fixtures', 'class_fixtures', 'submodule_name', moar_module)
            ])
            l = Loaddata()
            l.stdout = sys.stdout
            l.stderr = sys.stderr
            l.handle('some_fixtures', 'moar_fixtures')
            self.assertEqual(Company.objects.count(), 1)
            self.assertEqual(Employee.objects.count(), 2)
            self.assertEqual(EmployeeHistory.objects.count(), 2)
            self.assertEqual(Band.objects.count(), 1)
            self.assertEqual(Musician.objects.count(), 1)
            self.assertEqual(Membership.objects.count(), 1)
        finally:
            settings.FIXTURE_PACKAGES = old_pkgs
    
    def test_appname_shadows_fixturename(self):
        """
        Despite ``class_fixtures.tests`` having a ``tests.json`` fixture in
        its ``fixtures`` directory, ``manage.py loaddata tests`` will not load
        it, since it gets interpreted as a command to load all of the class
        fixtures in the first-level submodules of the ``fixtures`` package of
        the "tests" app. ``manage.py loaddata tests.json`` will still load it,
        however.
        """
        call_command('loaddata', 'tests', verbosity=0)
        # Stuff from tests.json must not appear
        self.assertEqual(Band.objects.filter(pk__in=[666, 667, 668]).count(), 0)
        # fixtures.some_fixtures and fixtures.other_fixtures contents combined
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(MetalBand.objects.count(), 1)
        self.assertEqual(Musician.objects.count(), 2)
        self.assertEqual(Roadie.objects.count(), 3)
        self.assertEqual(Membership.objects.count(), 2)
        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(Employee.objects.count(), 4)
        self.assertEqual(EmployeeHistory.objects.count(), 4)
    
    def test_app_with_no_fixtures(self):
        """
        When run against an app name with no fixtures, "No fixtures found\n"
        should get printed.
        """
        with string_stdout() as output:
            call_command('loaddata', 'testapp_no_fixtures', verbosity=1)
            self.assertEqual(output.getvalue(), 'No fixtures found.\n')
    
    def test_initial_data_loading(self):
        """
        The fixtures directory/package of the "tests" app contains an
        initial_data.json fixture as well as an initial_data.py fixture
        module. Both load one Party and one Politician object into the
        database.
        """
        # Initial data will be loaded when we arrive here, so just assert the
        # correct object amounts.
        self.assertEqual(Party.objects.count(), 2)
        self.assertEqual(Politician.objects.count(), 2)
    
    def test_django_fallback(self):
        """
        Our loaddata override should pass fixture labels on for Django to
        attempt to load in the following cases:
        
        ``fixtures = ["something"]`` or ``loaddata something``
          Only when "something" does not parse to an app name or the name of a
          ``fixtures.something`` module of an installed app.
        
        ``fixtures = ["something.json"]`` or ``loaddata something.json``
          Django will always handle these.
        
        initial_data
          Django's search for initial_data fixtures will always take place
          after django-class-fixtures has completed its own initial_data run.
          Mentioned here for completeness, tested in test_initial_data_loading
        """
        # Loads tests/fixtures/app_level_fixture.json
        call_command('loaddata', 'app_level_fixture', verbosity=0)
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual(MetalBand.objects.count(), 1)
        self.assertEqual(Musician.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 3)
        self.assertEqual(Roadie.objects.count(), 1)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Employee.objects.count(), 2)
        self.assertEqual(EmployeeHistory.objects.count(), 2)
        
        # Loads tests/testproject/project_fixtures/project_level_fixtures.json
        old_fixture_dirs = settings.FIXTURE_DIRS
        settings.FIXTURE_DIRS = (os.path.join(os.path.dirname(os.path.abspath(__file__)), "testproject/project_fixtures"),)
        try:
            call_command('loaddata', 'project_level_fixture.json', verbosity=0)
        finally:
            settings.FIXTURE_DIRS = old_fixture_dirs
        # No clearing the DB before, just add the counts of the two fixtures
        self.assertEqual(Band.objects.count(), 4)
        self.assertEqual(MetalBand.objects.count(), 2)
        self.assertEqual(Musician.objects.count(), 4)
        self.assertEqual(Membership.objects.count(), 6)
        self.assertEqual(Roadie.objects.count(), 2)


class DjangoLoaddataOutputParsingTests(TestCase):
    """
    The output of Django's ``loaddata`` command is parsed to add its reported
    counts to those of our own ``loaddata`` as well as to pass through any
    other messages to the user when higher verbosity levels are used.
    """
    def test_single_fixture_output(self):
        output = "Installed 2 object(s) from 1 fixture(s)\n"
        object_count, fixture_count, other_msgs = process_django_output(output)
        self.assertEqual(object_count, 2)
        self.assertEqual(fixture_count, 1)
        self.assertEqual(len(other_msgs), 0)
    
    def test_multiple_fixture_output(self):
        # Include one line of alternate format output, from which we don't
        # actually bother extracting the extra information yet.
        output = "Installed 2 object(s) from 1 fixture(s)\n" \
            "Installed 4 object(s) from 1 fixture(s)\n" \
            "Installed 7 object(s) from 2 fixture(s)\n" \
            "Installed 4 object(s) (of 6) from 1 fixture(s)\n"
        object_count, fixture_count, other_msgs = process_django_output(output)
        self.assertEqual(object_count, 17)
        self.assertEqual(fixture_count, 5)
        self.assertEqual(len(other_msgs), 0)
    
    def test_fixture_and_other_outputs_mixed(self):
        output = "Loading 'foobar' fixtures...\n" \
            "Checking /tmp/what/no for fixtures...\n" \
            "Installed 37 object(s) from 1 fixture(s)\n" \
            "Ha ha ha ha halibut.\n"
        object_count, fixture_count, other_msgs = process_django_output(output)
        self.assertEqual(object_count, 37)
        self.assertEqual(fixture_count, 1)
        self.assertEqual(len(other_msgs), 3)


class MultiDBTests(TestCase):
    """
    See tests.runtests.AlternateDBTestRouter for details about the custom
    routing scheme used here.
    
    Note that these tests only run successfully if run via ``python setup.py
    test`` from the source checkout, not when run via ``manage.py test`` as
    part of a Django project.
    
    In the former case, we can use class_fixtures.tests.runtests to set up the
    exact multi-db and routing circumstances that we need here. In the latter
    case, conf.settings comes preconfigured with unknown project-level
    settings regarding databases, and we'd have to monkeypatch django.conf
    and/or django.db stuff on the fly to temporarily create the precise
    database conditions that these tests expect, which just doesn't seem to
    work (I've tried several approaches).
    
    If you know of a way to make these tests run successfully with ``manage.py
    test`` in any arbitrary project that uses class_fixtures, patches are more
    than welcome. For now these just automatically pass in that case, see
    the setUp method.
    """
    multi_db = True
    
    def setUp(self):
        from django.db import connections, router
        from class_fixtures.tests.runtests import AlternateDBTestRouter
        self.do_tests = False
        if 'alternate' in connections.databases.keys() and \
            any([isinstance(r, AlternateDBTestRouter) for r in router.routers]):
            self.do_tests = True
            
    def test_initial_data_in_dbs(self):
        """
        ``Party`` and ``Politician`` model schemas should not appear in the
        "alternate" database.
        """
        if self.do_tests:
            # Already there via syncdb, no need to create
            self.assertEqual(Party.objects.count(), 2)
            self.assertEqual(Politician.objects.count(), 2)
            from django.db.utils import DatabaseError
            self.assertRaises(DatabaseError, Party.objects.using('alternate').count)
            self.assertRaises(DatabaseError, Politician.objects.using('alternate').count)
    
    def test_alternate_database(self):
        """
        Explicitly assign fixtures to a non-default database.
        """
        if self.do_tests:
            band_fixture = Fixture(Band)
            band_fixture.add(1, name="Nuns N' Hoses")
            band_fixture.add(2, name='Led Dirigible')
            roadie_fixture = Fixture(Roadie)
            roadie_fixture.add(1, name='Marshall Amp', hauls_for=[band_fixture.m2m(1), band_fixture.m2m(2)])
            call_command('loaddata', band_fixture, roadie_fixture, database='alternate', verbosity=0)
            self.assertEqual(Band.objects.using('alternate').count(), 2)
            self.assertEqual(Roadie.objects.using('alternate').count(), 1)
            self.assertEqual(Band.objects.count(), 0)
            self.assertEqual(Roadie.objects.count(), 0)
            self.assertEqual(Roadie.objects.using('alternate').get(name='Marshall Amp').hauls_for.count(), 2)
            self.assertEqual(Band.objects.using('alternate').get(name="Nuns N' Hoses").roadie_set.count(), 1)
            self.assertEqual(Band.objects.using('alternate').get(name='Led Dirigible').roadie_set.count(), 1)


class ErrorConditionTests(TestCase):
    def test_adding_duplicate_pk(self):
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses")
        self.assertRaises(FixtureUsageError, band_fixture.add, 1, name='Led Dirigible')
    
    def test_illegal_reverse_fk_assignment(self):
        employee_fixture = Fixture(Employee)
        # This specific example would fail at the Django level due to
        # Employee.company not being null=True, but we expect failure before
        # getting to that level, so using Employee for this is fine.
        employee_fixture.add(1, name='Andy Depressant', manager=None)
        company_fixture = Fixture(Company)
        self.assertRaises(RelatedObjectError, company_fixture.add, 1, name='Macrohard', employee_set=employee_fixture.fk(1))
    
    def test_circular_dependency(self):
        company_fixture = Fixture(Company)
        employee_fixture = Fixture(Employee)
        company_fixture.add(1, name='Dewey, Cheatem & Howe')
        # Trying to be each other's managers
        employee_fixture.add(1, name='Sly M. Ball', company=company_fixture.fk(1), manager=employee_fixture.fk(2))
        employee_fixture.add(2, name='Mei Ting', company=company_fixture.fk(1), manager=employee_fixture.fk(1))
        company_fixture.load()
        self.assertRaises(RelatedObjectError, employee_fixture.load)
    
    def test_non_iterable_m2m_definition(self):
        band_fixture = Fixture(Band)
        band_fixture.add(1, name="Nuns N' Hoses")
        roadie_fixture = Fixture(Roadie)
        # hauls_for requires a one-item iterable
        self.assertRaises(FixtureUsageError, roadie_fixture.add, 1, name='Marshall Amp', hauls_for=band_fixture.m2m(1))
