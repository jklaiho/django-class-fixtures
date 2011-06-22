from django.core.serializers.base import SerializationError, DeserializationError
from django.core.serializers.python import _get_model
from django.db import models

def dump_class_fixtures(objects, stream, **options):
    """
    Generate fixture modules.
    """
    encoding = 'utf-8'
    
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
    
    model_imports = ''
    for app, models in apps_models.items():
        # Is it possible for a model to not *also* be available in
        # appname.models? If yes, remove the hardcoding and get the correct
        # module by looking at the Model object.
        model_imports += 'from %s.models import %s\n' % (app, ', '.join(sorted(models)))
    
    stream.write(
        '# -*- coding: {encoding} -*-\n'
        'from class_fixtures.models import Fixture\n'
        '{imports}\n\n'.format(encoding=encoding, imports=model_imports)
    )
