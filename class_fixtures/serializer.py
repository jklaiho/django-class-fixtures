from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.python import Deserializer as PythonDeserializer

from class_fixtures.utils.serialization import dump_class_fixtures

class Serializer(PythonSerializer):
    """
    Serialize a QuerySet (or just a list of objects) into a complete
    class-based fixture module, loadable by the ``loaddata`` override included
    in django-class-fixtures.

    Same as Django's serializers, the output still has to be manually
    piped into or otherwise saved as a file in a valid fixture location.
    """
    internal_use_only = False

    def end_serialization(self):
        dump_class_fixtures(self.objects, self.stream, **self.options)

    def getvalue(self):
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()
