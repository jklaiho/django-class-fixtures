"""
Overridden loaddata command for class-based fixtures, with a fallback to the
original command for traditional file-based fixtures.
"""
import sys
import types
from pkgutil import walk_packages
from StringIO import StringIO

from django.core.management.base import BaseCommand
from django.core.management.commands.loaddata import Command as OriginalCommand
from django.core.management.color import no_style
from django.db import connections, transaction, DEFAULT_DB_ALIAS

from class_fixtures.exceptions import FixtureUsageError
from class_fixtures.utils.loaddata import (associate_handlers,
    get_fixtures_from_module, load_initial_data_modules, 
    process_django_output)
try:
    from collections import OrderedDict # Python 2.7 onwards
except ImportError:
    from class_fixtures.utils.ordereddict import OrderedDict

DjangoLoaddata = OriginalCommand()

class Command(BaseCommand):
    help = 'Installs the named fixture(s) in the database. These can be '\
        'file names, names of apps, or "appname.fixture_name" references.'
    args = DjangoLoaddata.args
    option_list = DjangoLoaddata.option_list
    
    def handle(self, *fixture_labels, **options):
        using = options.get('database', DEFAULT_DB_ALIAS)
        connection = connections[using]
        self.style = no_style()
        show_traceback = options.get('traceback', False)
        commit = options.get('commit', True)
        
        # I'm sure there is a valid reason why Django's loaddata does this,
        # so I'm just going to replicate its behaviour.
        cursor = connection.cursor()
        
        if commit:
            transaction.commit_unless_managed(using=using)
            transaction.enter_transaction_management(using=using)
            transaction.managed(True, using=using)
        
        total_object_count = 0
        total_fixture_count = 0
        do_initial_data = False
        captured_outputs = []
        original_verbosity = options.get('verbosity')
        # Mark this loaddata run as a special case for syncdb loading.
        # Django's loaddata will be run first, ours second.
        if fixture_labels == ('initial_data',):
            # Assign a special handler type for initial data
            fixture_handlers = [('initial_data', 'both_for_initial', None, None)]
        else:
            # Build a list of (label, handler, type, resolved_object) tuples.
            fixture_handlers = associate_handlers(fixture_labels)
        
        for label, handler, type_, obj in fixture_handlers:
            if handler in ['django', 'both_for_initial']:
                captured_stdout = StringIO()
                # Need to assign manually; normally available to handle() via
                # BaseCommand.execute(), but not when we're using it this way.
                DjangoLoaddata.stdout = captured_stdout
                DjangoLoaddata.stderr = self.stderr
                # Capturing fixture counts from stdout requires forcing the
                # verbosity option to a minimum of 1. If set higher by the
                # user, respect that. Collect any extra messages for display.
                if 'verbosity' in options:
                    options['verbosity'] = 1 if options['verbosity'] == 0 else options['verbosity']
                else:
                    options['verbosity'] = 1
                # We will either be in our own transaction handling or that of
                # the script that called us, so disable transaction management
                # inside Django's loaddata
                options['commit'] = False
                try:
                    DjangoLoaddata.handle(label, **options)
                except Exception:
                    if commit:
                        transaction.rollback(using=using)
                        transaction.leave_transaction_management(using=using)
                    raise
                django_object_count, django_fixture_count, other_msgs = process_django_output(captured_stdout.getvalue())
                captured_stdout.close()
                total_object_count += django_object_count
                total_fixture_count += django_fixture_count
                captured_outputs.extend(other_msgs)
            
            if handler in ['class_fixtures', 'both_for_initial']:
                if type_ == 'instance':
                    fixtures = [label]
                elif type_ == 'module':
                    fixtures = get_fixtures_from_module(label)
                elif type_ == 'submodule_name':
                    # obj is a reference to an individual submodule of
                    # the fixtures package of some app.
                    fixtures = get_fixtures_from_module(obj)
                elif type_ == 'app_label':
                    # obj is a reference to the fixtures package of the
                    # app named in the label. Load all the fixture modules 
                    # contained within, excluding initial_data.
                    fixtures = []
                    for importer, module_name, is_pkg in walk_packages(obj.__path__):
                        if module_name == 'initial_data':
                            continue
                        submodule = importer.find_module(module_name).load_module(module_name)
                        submod_fixtures = get_fixtures_from_module(submodule)
                        for submod_fixture in submod_fixtures:
                            # In case the user has a deeper submodule hierarchy in place
                            # with fixtures imported from submodule to submodule, make sure no fixture
                            # is included in the list twice through submodule discovery.
                            if submod_fixture not in fixtures:
                                fixtures.append(submod_fixture)
                
                try:
                    if handler != 'both_for_initial':
                        for fixture in fixtures:
                            object_count = fixture.load(using=using)
                            total_object_count += object_count
                            total_fixture_count += 1
                    else:
                        object_count, fixture_count = load_initial_data_modules(using=using)
                        total_object_count += object_count
                        total_fixture_count += fixture_count
                except (SystemExit, KeyboardInterrupt):
                    raise
                except Exception:
                    import traceback
                    if commit:
                        transaction.rollback(using=using)
                        transaction.leave_transaction_management(using=using)
                    if show_traceback:
                        traceback.print_exc()
                    else:
                        self.stderr.write(
                            self.style.ERROR("Problem installing class-based fixtures: %s" %
                            ''.join(traceback.format_exception(sys.exc_type,
                                 sys.exc_value, sys.exc_traceback))))
                    return
        if commit:
            transaction.commit(using=using)
            transaction.leave_transaction_management(using=using)
        
        # Same MySQL workaround as in Django's loaddata
        if commit:
            connection.close()
        
        if total_fixture_count == 0:
            if original_verbosity >= 1:
                self.stdout.write("No fixtures found.\n")
        else:
            if original_verbosity >= 2 and captured_outputs:
                self.stdout.write('\n'.join(captured_outputs))
            if original_verbosity >= 1:
                # The original loaddata has another possible output format
                # used when less objects were loaded than were present in the
                # fixtures, but I don't care enough to implement it.
                self.stdout.write("Installed %d object(s) from %d fixture(s)\n" %
                    (total_object_count, total_fixture_count))
        