try:
    from collections import OrderedDict # Python 2.7 onwards
except ImportError:
    from class_fixtures.utils.ordereddict import OrderedDict

from django.core.serializers.base import SerializationError, DeserializationError
from django.core.serializers.python import _get_model


class ClassicReprOrderedDict(OrderedDict):
    """An OrderedDict subclass with a custom, dict-like __repr__ method."""
    def __repr__(self):
        if not self:
            return '{}'
        itemlist = []
        for k, v in self.items():
            itemlist.append("%r: %r" % (k, v))
        return '{%s}' % ', '.join(itemlist)

def dump_class_fixtures(objects, stream, **options):
    """
    Generate fixture modules.
    """
    # Construct and output the import rows
    apps_models = {}
    for identifier in [d['model'] for d in objects]:
        appname = identifier.split('.')[0]
        if appname not in apps_models:
            apps_models[appname] = []
        try:
            Model = _get_model(identifier)
        except DeserializationError:
            raise SerializationError('Cannot resolve "%s" to a model class' % identifier)
        
        if Model._meta.object_name not in apps_models[appname]:
            apps_models[appname].append(Model._meta.object_name)
    
    model_imports = []
    for app, models in apps_models.items():
        model_imports.append('from %s.models import %s' % (app, ', '.join(sorted(models))))
    
    stream.write(
        '# -*- coding: utf-8 -*-\n'
        'from class_fixtures.models import Fixture\n'
        '%s\n\n' % '\n'.join(model_imports)
    )
    
    # Construct and output the Fixture instances
    fixture_instantiations = []
    for app, models in apps_models.items():
        for model in models:
            fixture_instantiations.append('%s_%s_fixture = Fixture(%s)' % (
                app, model.lower(), model
            ))
    
    stream.write('\n'.join(fixture_instantiations) + '\n\n')
    
    # Construct and output the Fixture.add() calls in the dependency-resolved
    # order that 'objects' is in. The field names are in the "fields"
    # dictionary which, being a dictionary, is unordered. To make the output
    # predictable and testable, we use a subclass of OrderedDict that produces
    # alphabetized dict-like repr() output.
    for pk, identifier, fields in [(d['pk'], d['model'], d['fields']) for d in objects]:
        app, model = identifier.split('.')
        kwargs = ClassicReprOrderedDict(sorted(fields.items(), key=lambda field: field[0]))
        stream.write('%s_%s_fixture.add(%s, **%s)\n' % (app, model, pk, repr(kwargs)))
