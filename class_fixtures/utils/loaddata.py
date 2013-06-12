"""Utility methods for the overridden loaddata command"""
import re
import types
from collections import Iterable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers import get_public_serializer_formats
from django.db.models.loading import get_apps
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

from class_fixtures.exceptions import FixtureUsageError
from class_fixtures.models import Fixture


def associate_handlers(fixture_labels):
    """
    Examines the fixture labels, determining which should be loaded by
    django-class-fixtures and which by Django.

    Returns a list of (label, handler, type, obj) tuples like this::

        [
            ('fixture.json', 'django', None, None),
            (fixture_instance, 'class_fixtures', 'instance', None),
            (fixture_module, 'class_fixtures', 'module', None)
            ('appname.fixturemodule', 'class_fixtures', 'submodule_name', submodule_reference)
            ('appname', 'class_fixtures', 'app_label', fixtures_package_reference)
        ]

    ``type`` is None for Django fixtures, or one of the following identified
    label types for class-based fixtures: 'instance', 'module', 'app_label',
    'submodule_name'

    ``obj`` is None for Django fixtures, or one of the following for class-
    based fixtures:
      - a reference to a submodule of the ``someapp.fixtures`` package
      - a reference to the ``someapp.fixtures`` package itself
      - None where the instance or module reference is itself the ``label``
        item of the tuple and no further resolving was necessary

    """
    handlers = []
    django_formats = get_public_serializer_formats()

    for label in fixture_labels:
        if isinstance(label, Fixture):
            handlers.append((label, 'class_fixtures', 'instance', None))
        elif type(label) == types.ModuleType:
            handlers.append((label, 'class_fixtures', 'module', None))
        elif isinstance(label, basestring):
            label_components = label.split('.')
            # 'some.fixture.json' or "another_fixture.xml" etc.
            if label_components[-1] in django_formats:
                handlers.append((label, 'django', None, None))
            # If the first part of a dot-split fixture label matches the name
            # of a Django app (i.e. a package with a models.py file), it's
            # going to be handled by django-class-fixtures.
            #
            # Here we create appropriate handler tuples for both "appname" and
            # "appname.fixture_module", resolving into the correct modules
            # for loaddata to use.
            #
            # A gotcha: if you have an app named "foobar", and inside the
            # fixtures directory of any app a fixture file named e.g.
            # "foobar.json", that fixture file will only be loaded if you
            # run "loaddata foobar.json". "loaddata foobar" will only load the
            # fixtures in the foobar app due to the code below. So don't
            # do duplicate names, and use extensions if you do.
            elif label_components[0] in [app.__name__.split('.')[-2] for app in get_apps()]:
                # Resolve the app label into an importable path string
                idx = [app.__name__.split('.')[-2] for app in get_apps()].index(label_components[0])
                path = '.'.join(get_apps()[idx].__name__.split('.')[:-1])
                if len(label_components) == 1:
                    # Place a reference to the fixtures package of the app
                    # into the handler tuple
                    try:
                        package = import_module('%s.fixtures' % path)
                        handlers.append((label, 'class_fixtures', 'app_label', package))
                    except ImportError:
                        raise FixtureUsageError('The "%s" app does not have a "fixtures" package.' % label_components[0])
                elif len(label_components) == 2:
                    # Place a reference to the desired submodule of the
                    # fixture package of the named app into the handler tuple.
                    try:
                        submodule = import_module('%s.fixtures.%s' % (path, label_components[1]))
                        handlers.append((label, 'class_fixtures', 'submodule_name', submodule))
                    except ImportError, e:
                        if "No module named" in str(e):
                            raise FixtureUsageError('No module named "%s" in "%s.fixtures"' % (label_components[1], label_components[0]))
                        else:
                            raise e
                else:
                    raise FixtureUsageError('Fixture labels referring to apps must be one of "appname" or "appname.fixturename"')
            else:
                # The label is a string like "blarbagh" or "what.ever.now"
                # which can be one or more of:
                # a) a Django fixture file with any of the registered
                #    fixture extensions ("blarbagh.json" or
                #    "what.ever.now.xml")
                # b) the name of a module in some app's fixtures package
                #    ("blarbagh" only, can't have "what.ever.now.py"),
                # c) the name of a module in one of the packages listed in
                #    settings.FIXTURE_PACKAGES ("blarbagh" only, again)
                #
                # Since Django will load all the fixtures that it finds with
                # this name, we'll do the same with fixture modules. A label
                # may thus appear in the resulting handler list multiple
                # times; always once with the 'django' handler and 0-N times
                # with the 'class_fixtures' handler, assuming any matching
                # modules.
                handlers.append((label, 'django', None, None))

                for appname in settings.INSTALLED_APPS:
                    try:
                        submodule = import_module('%s.fixtures.%s' % (appname, label))
                        handlers.append((label, 'class_fixtures', 'submodule_name', submodule))
                    except ImportError, e:
                        if "No module named" in str(e):
                            continue
                        else:
                            raise e

                if check_fixture_packages_setting():
                    # If the string in FIXTURE_PACKAGES is valid,
                    # further ImportErrors regarding nonexistent modules
                    # are to be expected
                    for package_path in settings.FIXTURE_PACKAGES:
                        try:
                            submodule = import_module('%s.%s' % (package_path, label))
                            handlers.append((label, 'class_fixtures', 'submodule_name', submodule))
                        except ImportError, e:
                            if "No module named" in str(e):
                                continue
                            else:
                                raise e

        else:
            raise FixtureUsageError('Invalid fixture label "%s"' % label)
    return handlers


def gather_initial_data_fixtures(using=None):
    """
    Iterate through the ``fixtures`` package of all installed apps and any
    packages in settings.FIXTURE_PACKAGES, looking for contained initial_data
    modules and returning a list of all that are found.
    """
    initial_fixtures = []
    for appname in settings.INSTALLED_APPS:
        try:
            package = import_module('%s.fixtures' % appname)
        except ImportError:
            continue
        try:
            if module_has_submodule(package, 'initial_data'):
                initial_data = import_module('%s.fixtures.initial_data' % appname)
                initial_fixtures.extend(get_fixtures_from_module(initial_data))
        except ImportError, e:
            raise ImportError('In %s.fixtures.initial_data: %s' % (appname, e))

    if check_fixture_packages_setting():
        for package_path in settings.FIXTURE_PACKAGES:
            package = import_module(package_path)
            try:
                if module_has_submodule(package, 'initial_data'):
                    initial_data = import_module('%s.initial_data' % package_path)
                    initial_fixtures.extend(get_fixtures_from_module(initial_data))
            except ImportError, e:
                raise ImportError('In %s.initial_data: %s' % (package_path, e))

    return initial_fixtures

def check_fixture_packages_setting():
    if getattr(settings, 'FIXTURE_PACKAGES', False):
        if not isinstance(settings.FIXTURE_PACKAGES, Iterable) or not all([isinstance(m, basestring) for m in settings.FIXTURE_PACKAGES]):
            raise ImproperlyConfigured('settings.FIXTURE_PACKAGES must be an iterable of strings (package paths in dotted path notation)')
        for package_path in settings.FIXTURE_PACKAGES:
            try:
                import_module(package_path)
            except ImportError:
                raise ImportError('settings.FIXTURE_PACKAGES: %s is not an importable Python package' % package_path)
        return True
    else:
        return False

def get_fixtures_from_module(module):
    """
    Returns a list of all the ``Fixture`` instances contained in ``module``.
    """
    fixture_list = []
    module_attrs = dir(module)
    for attr_name in module_attrs:
        attribute = getattr(module, attr_name)
        if isinstance(attribute, Fixture):
            fixture_list.append(attribute)
    return fixture_list


def process_django_output(output):
    """
    Django's loaddata, depending on the verbosity setting, will output various
    things during and after the fixture loading process. It's all captured
    by our loaddata override. This method extracts the reported object and
    fixture counts from the output, as well as any extra messages that were
    printed with higher verbosity levels.

    Returns a (object_count, fixture_count, [other_msg_list]) tuple.
    """
    counts = []
    other_msgs = []
    output_msgs = output.split('\n')
    pattern = re.compile(r'Installed (?P<object_count>\d+) object\(s\)(?: \(of \d+\))? from (?P<fixture_count>\d+) fixture\(s\)')

    for msg in output_msgs:
        if not msg: continue # skip blanks created by the \n split
        match = pattern.search(msg)
        if match:
            counts.append(match.groups())
        else:
            other_msgs.append(msg)

    # Everybody loves nested list comprehensions.
    total_counts = [sum(z) for z in zip(*[(int(tup[0]), int(tup[1])) for tup in counts])] or [0, 0]

    return (total_counts[0], total_counts[1], other_msgs)
