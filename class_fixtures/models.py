try:
    from collections import OrderedDict # Python 2.7 onwards
except ImportError:
    from class_fixtures.utils.ordereddict import OrderedDict
from collections import Iterable

from django.db import models, router
from django.db.models.fields.related import (
    SingleRelatedObjectDescriptor as srod,
    ManyRelatedObjectsDescriptor as mrod,
    ReverseSingleRelatedObjectDescriptor as rsrod,
    ReverseManyRelatedObjectsDescriptor as rmrod,
    )
from class_fixtures.exceptions import FixtureUsageError, RelatedObjectError

try:
    from milkman.dairy import milkman
except ImportError:
    milkman = None

__all__ = ['Fixture']

class Fixture(object):
    """
    A class-based fixture. Relies on the overridden ``loaddata`` command of
    django-class-fixtures.
    
    Each ``Fixture`` instance is tied to one model class. Instances have an
    ``add`` method which receives a primary key value followed by the same
    keyword arguments that would be used to create instances of that model.
    
    You can have multiple fixtures per model, like so::
    
        admin_fixture = Fixture(User)
        staff_fixture = Fixture(User)
    
    You can then ``add()`` different sets of User objects to each.
    
    Fixture instances have a ``load`` method, which does the work of actually
    saving the model objects and their relations into the database.
    
    For the full details, see the documentation.
    """
    def __init__(self, model, raw=False):
        # PK values as keys, object definition kwargs as values.
        # Populated by add() calls.
        self._kwarg_storage = OrderedDict()
        # Stores references to Fixture instances that need to be loaded
        # before this one. Populated by add() calls.
        self._dependencies = []
        # Set to False just before the first loading attempt.
        self._adding_allowed = True
        # Enable DeserializedObject-like raw saves that bypass custom save
        # methods (which Django's loaddata does)
        self.raw = raw
        
        # Allow for custom model classes, not just models.Model subclasses.
        if isinstance(model, models.base.ModelBase):
            self.model = model
        else:
            raise TypeError('%s is not a Django model class' % model.__name__)
    
    def add(self, *args, **kwargs):
        """
        A tiny gatekeeper method. Checks that ``args`` contains precisely one
        item, assumed to be a valid primary key for an instance of
        ``self.model``. See ``_add`` for the actual instance adding
        functionality.
        
        The reason this method exists is that running some_fixture.add()
        without the positional PK parameter (a common mistake in handmade
        fixtures) raises an unhelpful TypeError that can't be caught in _add.
        """
        if len(args) != 1:
            raise FixtureUsageError('Fixture.add() must receive a primary key value as its single positional argument')
        self._add(*args, **kwargs)
    
    def _add(self, pk, **kwargs):
        """
        Adds model instance definitions to the Fixture instance. Does *not*
        write anything to the database (that is done when the ``load`` method
        gets run later).
        
        The ``pk`` parameter is the hard-coded primary key for the object.
        Hard-coding is needed for accuracy with how Django's loaddata works
        (assumes serialized primary keys, overwrites existing objects when
        running loaddata).
        
        The remaining keyword arguments are very close to those you would you
        would give to a model instance constructor or a manager's ``create``
        method. This is too complex a topic for this docstring, see the
        documentation on defining relations between objects and more.
        """
        if not self._adding_allowed:
            raise FixtureUsageError('Cannot add more objects to a loaded fixture')
        if pk in self._kwarg_storage:
            raise FixtureUsageError('Primary key %s already added to another object in the same fixture.' % pk)
        
        definitions = self._build_relations(**kwargs)
        
        definitions.update({'pk': pk})
        self._kwarg_storage[pk] = definitions
    
    def add_random(self, pk, **kwargs):
        """
        Creates randomly generated model instances using Milkman, if it is
        installed. Raises a FixtureUsageError if not.
        
        Since the point of this integration is to be able to easily and safely
        mix generated and predefined Fixture instances, we still require
        explicit primary keys (milkman does not).
        """
        if milkman is None:
            raise FixtureUsageError('Milkman is not installed, Fixture.add_random() not available.')
        if pk in self._kwarg_storage:
            raise FixtureUsageError('Primary key %s already added to another object in the same fixture.' % pk)
        
        definitions = self._build_relations(**kwargs)
        
        definitions.update({'pk': pk})
        self._kwarg_storage[pk] = DelayedMilkmanDelivery(**definitions)
    
    def _build_relations(self, **kwargs):
        for fieldname, value in kwargs.items():
            field_is_m2m = False
            # The name given to a ManyToManyField in a model definition will
            # actually become a descriptor with that name. In the model where
            # the field is included in, it becomes a
            # ReverseManyRelatedObjectsDescriptor. In the "target" model, a
            # ManyRelatedObjectsDescriptor (foobar_set by default) is created.
            # See if the field name we're examining is either of those.
            if any([isinstance(getattr(self.model, fieldname, None), m2m_descriptor) for m2m_descriptor in [mrod, rmrod]]):
                field_is_m2m = True
                # M2Ms must be expressed as iterables (iterables of iterables
                # in case of natural keys). A single natural key tuple will
                # pass this check, but fail another one later on.
                if not isinstance(value, Iterable):
                    raise FixtureUsageError('Non-iterable value %s passed to '\
                        'the "%s" M2M field in an add() call.' % (value, fieldname))
            
            # Case 1: Relations to objects that don't yet exist but are
            # defined in this or some other Fixture instance. They are 
            # represented as DelayedRelatedObjectLoader instances.
            
            # Normalize to a list to keep the logic below simpler and DRYer
            if not isinstance(value, Iterable):
                value_list = [value]
            else:
                value_list = value
            
            if any([isinstance(v, DelayedRelatedObjectLoader) for v in value_list]):
                # Add the Fixture instances that DelayedRelatedObjectLoaders
                # point to as dependencies that need to be loaded before this
                # Fixture.
                for v in value_list:
                    if isinstance(v, DelayedRelatedObjectLoader):
                        if self in v.fixture_instance._dependencies:
                            raise RelatedObjectError('Circular dependency between '\
                                'Fixture instances for %s and %s' % 
                                self.model, v.fixture_instance.model)
                        if v.fixture_instance not in self._dependencies and v.fixture_instance != self:
                            self._dependencies.append(v.fixture_instance)
            
            # Case 2: Relating to pre-existing objects, not ones getting
            # created in the fixture loading process.
            
            # The model class itself won't have attributes named after
            # its fields, except the descriptors created by FK/M2M/O2O
            # fields, which are precisely what we're after here.
            descriptor = getattr(self.model, fieldname, None)
            # Find the other end of the relation
            if descriptor:
                if any([isinstance(descriptor, rev_rel_descriptor) for rev_rel_descriptor in [rsrod, rmrod]]):
                    # fieldname refers to a descriptor in the model that
                    # contains the FK/M2M/O2O field definition
                    other_model = descriptor.field.related.parent_model
                elif any([isinstance(descriptor, rel_descriptor) for rel_descriptor in [srod, mrod]]):
                    # fieldname refers to the automatically created
                    # attribute in the target model of the FK/M2M/O2O
                    other_model = descriptor.related.model
                else:
                    from django.db.models.fields.related import ForeignRelatedObjectsDescriptor
                    if isinstance(descriptor, ForeignRelatedObjectsDescriptor):
                        raise RelatedObjectError('Cannot define foreign key relation from the target end')
                    else:
                        raise RelatedObjectError('Unknown descriptor-related '\
                            'error condition. Please file a bug report for '\
                            'django-class-fixtures.')
                
                # Turn any values that don't evaluate to boolean False and are
                # not DelayedRelatedObjectLoaders into RelatedObjectLoader
                # instances.
                if value:
                    if not field_is_m2m and not isinstance(value, DelayedRelatedObjectLoader):
                        kwargs.update({fieldname: RelatedObjectLoader(other_model, value)})
                    elif field_is_m2m:
                        loaders = []
                        for v in value_list:
                            if not isinstance(v, DelayedRelatedObjectLoader):
                                loaders.append(RelatedObjectLoader(other_model, v))
                            else:
                                loaders.append(v)
                        kwargs.update({fieldname: loaders})
        
        return kwargs
    
    def load(self, using=None):
        """
        Creates model instances from the stored definitions and writes them
        to the database.
        
        You generally won't run this method by hand, as it's handled by the
        fixture discovery and loading process of the overridden ``loaddata``
        command.
        
        Returns the number of objects saved to the database.
        """
        self._adding_allowed = False
        saved_objects = {}
        
        # Load any unloaded dependencies of this instance first
        for dep in self._dependencies:
            saved_objects.update(dep.load(using=using))
        
        # Offload the actual processing to a FixtureLoader instance
        fl = FixtureLoader(self._kwarg_storage, self)
        saved_objects.update(fl.load(using=using, raw=self.raw))
        fl.create_m2m_relations(using=using)
        return saved_objects
    
    def get_object_by_pk(self, pk, using=None):
        try:
            return self.model._default_manager.db_manager(using).get(pk=pk)
        except self.model.DoesNotExist:
            raise RelatedObjectError('No %s object found with the primary key %s'\
                % (self.model._meta.object_name, pk))
    
    def _create_delayed_relation(self, pk):
        """
        Places DelayedRelatedObjectLoader instances as value placeholders in
        model definition kwargs. The ``load`` method will later parse these
        into the actual related objects.
        
        ``fk``, ``m2m`` and ``o2o`` are functionally identical aliases of this
        method to make fixture construction more self-documenting.
        """
        return DelayedRelatedObjectLoader(self, pk)
    fk = m2m = o2o = _create_delayed_relation


class FixtureLoader(object):
    """
    A utility class, throwaway instances of which are generated by
    ``Fixture.load``. Constructs objects from the ``kwarg_storage``
    OrderedDict, saves them to the database and builds any M2M relations.
    
    Enables keeping Fixture instances state-free regarding actual
    created objects.
    """
    def __init__(self, kwarg_storage, fixture_instance):
        self.kwarg_storage = kwarg_storage
        self.fixture_instance = fixture_instance
        # PKs as keys, dictionaries of all the M2M fields to which objects
        # need to be added to as values.
        self._pending_m2m = {}
        # PKs as keys, saved objects as values.
        self.saved = OrderedDict()
    
    def load(self, using=None, raw=False):
        """
        Does the actual work of creating objects from definitions stored in
        Fixture instances.
        
        Returns the number of objects saved to the database.
        """
        # Replace ObjectLoaders with the actual objects
        for pk, model_def in self.kwarg_storage.items():
            resolved_def = dict()
            for fieldname, value in model_def.items():
                # Do the magic of allowing M2M relation creation through an
                # iterable of values inlined in the object definition kwargs.
                # See if the field name is listed in the Model's M2M field
                # list. If yes, replace the assignment with a proper post-save
                # M2M addition.
                if any([isinstance(getattr(self.fixture_instance.model, fieldname, None), m2m_descriptor) for m2m_descriptor in [mrod, rmrod]]):
                    if isinstance(model_def, DelayedMilkmanDelivery):
                        # Milkman handles explicit M2Ms itself, no need to
                        # add to the list of relations created later. Just
                        # resolve to the real objects.
                        resolved_def[fieldname] = []
                        if isinstance(value, Iterable) and all([isinstance(v, ObjectLoader) for v in value]):
                            for v in value:
                                resolved_def[fieldname].append(v.get_related_object(using=using))
                        else:
                            raise RelatedObjectError('Invalid argument "%s" to a ManyToMany field' % value)
                    else:
                        # Save the M2M relations for later saving
                        if pk not in self._pending_m2m:
                            self._pending_m2m[pk] = {}
                        if fieldname not in self._pending_m2m[pk]:
                            self._pending_m2m[pk][fieldname] = []
                        # The value assigned to the field can be either a single
                        # M2M placeholder or an iterable of them.
                        if isinstance(value, Iterable) and all([isinstance(v, ObjectLoader) for v in value]):
                            for v in value:
                                self._pending_m2m[pk][fieldname].append(v.get_related_object(using=using))
                        else:
                            raise RelatedObjectError('Invalid argument "%s" to a ManyToMany field' % value)
                else:
                    # The field is not an M2M and thus supports
                    # "fieldname=value" assignment, so just get a reference to
                    # an actual object to replace the placeholder.
                    if isinstance(value, ObjectLoader):
                        resolved_def[fieldname] = value.get_related_object(using=using)
                    else:
                        resolved_def[fieldname] = value
            # Safe to modify, since we're iterating over the items() output,
            # not the dictionary itself.
            self.kwarg_storage[pk] = resolved_def
            
            if router.allow_syncdb(using, self.fixture_instance.model):
                if isinstance(model_def, DelayedMilkmanDelivery):
                    self.saved[pk] = milkman.deliver(self.fixture_instance.model, **resolved_def)
                else:
                    if raw:
                        # See the documentation on "raw mode" for an explanation
                        obj = self.fixture_instance.model(**resolved_def)
                        models.Model.save_base(obj, using=using, raw=True)
                        self.saved[pk] = obj
                    else:
                        obj = self.fixture_instance.model(**resolved_def)
                        obj.save(using=using)
                        self.saved[pk] = obj
        
        return self.saved
    
    def create_m2m_relations(self, using=None):
        """
        Writes any pending M2M relations to the database after the objects
        that are to relate to each other have been saved.
        """
        for pk, relations in self._pending_m2m.items():
            obj = self.fixture_instance.get_object_by_pk(pk, using=using)
            for rel_name, targets in relations.items():
                for target in targets:
                    getattr(obj, rel_name).add(target)


class ObjectLoader(object):
    """
    No-op base class for DelayedRelatedObjectLoader and RelatedObjectLoader,
    used to aid in ``isinstance`` calls in ``FixtureLoader.load``.
    """
    def __init__(self, *args, **kwargs):
        raise NotImplementedError('Use one of the child classes of ObjectLoader.')
    
    def get_related_object(self, using=None):
        raise NotImplementedError('Use one of the child classes of ObjectLoader.')


class DelayedRelatedObjectLoader(ObjectLoader):
    """
    A placeholder for actual related object references in model instance
    definitions stored in a Fixture, where those related objects are
    themselves contained in Fixtures. See RelatedObjectLoader for the
    equivalent for pre-existing objects.
    """
    def __init__(self, fixture_instance, pk):
        self.fixture_instance = fixture_instance
        self.pk = pk
    
    def get_related_object(self, using=None):
        return self.fixture_instance.get_object_by_pk(self.pk, using=using)


class RelatedObjectLoader(ObjectLoader):
    """
    When ``Fixture.add`` calls include non-DelayedRelatedObjectLoader values
    for relation field kwargs, RelatedObjectLoader instances are created as
    placeholders.
    
    Example::
        
        some_fixture = Fixture(SomeModel)
        some_fixture.add(name="foo", some_related_fk=12, some_m2m=[10, 18])
        some_fixture.add(name="bar", some_related_fk=obj1, some_m2m=[obj2, obj3])
    
    The values passed as the ``some_related_fk`` and ``some_m2m`` kwargs
    are seen by ``add`` to not be DelayedRelatedObjectLoaders, so the job of
    figuring out if and how to turn them into proper object instances is left
    to the ``get_related_object`` method of this class.
    
    See DelayedRelatedObjectLoader for the similar implementation of relations
    that live in Fixture instances.
    """
    def __init__(self, model, identifier):
        self.model = model
        # Either a PK value, a natural key tuple or a model instance.
        self.identifier = identifier
    
    def get_related_object(self, using=None):
        """
        When this gets called, what self.identifier contains is unknown.
        Figure it out and return an object reference.
        """
        # Is self.identifier already a model instance of the correct type?
        if isinstance(self.identifier, self.model):
            return self.identifier
        # Is self.identifier a natural key tuple?
        elif isinstance(self.identifier, Iterable) and hasattr(self.model._default_manager.db_manager(using), 'get_by_natural_key'):
            try:
                obj = self.model._default_manager.db_manager(using).get_by_natural_key(*self.identifier)
                return obj
            except self.model.DoesNotExist:
                # Pass, since it could be a list of PKs
                pass
        # Is self.identifier the PK value of an instance of the related model?
        else:
            try:
                obj = self.model._default_manager.db_manager(using).get(pk=self.identifier)
                return obj
            except self.model.DoesNotExist:
                raise RelatedObjectError('No %s objects with primary key %s exist.' % \
                    (self.model._meta.object_name, self.identifier)
                )


class DelayedMilkmanDelivery(dict):
    """
    No-op dictionary subclass to aid in identifying the use of Milkman in the
    loader methods. Not the most pythonic way, relying on isinstance for it,
    but the least work to fit this in with the logic that existed before
    Milkman support.
    """
    pass


from django.core.serializers import register_serializer
# Not thread safe according to the register_serializer docstring, don't know
# if it matters here or not.
register_serializer('class', 'class_fixtures.serializer')
