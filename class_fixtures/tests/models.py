from django.db import models

# For relationless, M2M, M2M w/through model and concrete inheritance testing
class Band(models.Model):
    name = models.CharField(max_length=255)


class MetalBand(Band):
    leather_pants_worn = models.BooleanField(default=True)


class Musician(models.Model):
    name = models.CharField(max_length=100)
    member_of = models.ManyToManyField(Band, through='Membership')


class Membership(models.Model):
    musician = models.ForeignKey(Musician)
    band = models.ForeignKey(Band)
    date_joined = models.DateField(null=True)
    instrument = models.CharField(max_length=100)


class Roadie(models.Model):
    name = models.CharField(max_length=100)
    hauls_for = models.ManyToManyField(Band)



# For normal FK, FK to self and non-inheritance OneToOneField testing
class Company(models.Model):
    name = models.CharField(max_length=100)


class Employee(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company)
    manager = models.ForeignKey('self', null=True)
    cog_in_the_machine = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if ' corp' in self.company.name.lower():
            self.cog_in_the_machine = True
        super(Employee, self).save(*args, **kwargs)


class EmployeeHistory(models.Model):
    employee = models.OneToOneField(Employee)
    date_joined = models.DateField()



# For natural key testing
class CompetencyManager(models.Manager):
    def get_by_natural_key(self, framework, level):
        return self.get(framework=framework, level=level)

class Competency(models.Model):
    LEVEL_CHOICES = (
        (0, "None"),
        (1, "Beginner"),
        (2, "Intermediate"),
        (3, "Advanced"),
        (4, "Guru"),
    )
    framework = models.CharField(max_length=100)
    level = models.SmallIntegerField(choices=LEVEL_CHOICES)

    objects = CompetencyManager()

    def natural_key(self):
        return (self.framework, self.level)

    class Meta(object):
        unique_together = (('framework', 'level'))


class JobPosting(models.Model):
    title = models.CharField(max_length=100)
    main_competency = models.ForeignKey(Competency, related_name='main_competency_for')
    additional_competencies = models.ManyToManyField(Competency, related_name='extra_competency_for')



# For initial data only, to prevent messing up object counts for other models
# in tests. Due to custom routing in tests.runtests.AlternateDBTestRouter, the
# schemas for these models will not be synched to the "alternate" database.
class Party(models.Model):
    name = models.CharField(max_length=100)


class Politician(models.Model):
    name = models.CharField(max_length=100)
    party = models.ForeignKey(Party)
    minimum_bribe = models.DecimalField(max_digits=10, decimal_places=2, null=True)



# For testing dumpdata with a complex model. Skip some fields whose serialized
# representation is identical to that of others, e.g. FileField == CharField.
class ComprehensiveModel(models.Model):
    bigint = models.BigIntegerField()
    boolean = models.BooleanField()
    char = models.CharField(max_length=255)
    date = models.DateField()
    datetime = models.DateTimeField()
    decimal = models.DecimalField(max_digits=6, decimal_places=2)
    floatf = models.FloatField()
    integer = models.IntegerField()
    nullboolean = models.NullBooleanField()
    text = models.TextField()
    time = models.TimeField()
