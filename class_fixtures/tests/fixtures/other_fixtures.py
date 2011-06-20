from class_fixtures.models import Fixture
from class_fixtures.tests.models import *

membership_fixture = Fixture(Membership)
band_fixture = Fixture(Band)
metalband_fixture = Fixture(MetalBand)
musician_fixture = Fixture(Musician)
roadie_fixture = Fixture(Roadie)

band_fixture.add(5, name="Bar Fighters")
metalband_fixture.add(6, name="Brutallica", leather_pants_worn=True)

musician_fixture.add(5, name="Hamish Jetfield")
musician_fixture.add(6, name="Dave Growl")

# Keyword-based FK target lookup
membership_fixture.add(7,
    musician = musician_fixture.fk(6),
    band = band_fixture.fk(5),
    date_joined = '2000-04-01',
    instrument = "All of them",
)

# Relation token -based FK target lookup
membership_fixture.add(8,
    musician = musician_fixture.fk(5),
    band = metalband_fixture.fk(6),
    date_joined = '1982-03-03',
    instrument = "Guitarrrr-ahh",
)

# Single M2M addition with a kwarg
roadie_fixture.add(3, name='Tats Brimhat', hauls_for=[band_fixture.m2m(5)])

# Two M2M additions with a list of kwargs
roadie_fixture.add(4, name='Blackie Teeshirt', hauls_for=[
    band_fixture.m2m(5), metalband_fixture.m2m(6)])

# Single M2M addition with a relation token
roadie_fixture.add(5, name='Ciggy Tardust', hauls_for=[metalband_fixture.m2m(6)])



company_fixture = Fixture(Company)
employee_fixture = Fixture(Employee)
employee_history_fixture = Fixture(EmployeeHistory)

company_fixture.add(2, name='FacelessCorp Inc.')
# Normal FK relationship to another model
employee_fixture.add(3, name='Ty Rant', company=company_fixture.fk(2))
# Same, plus a recursive FK relationship to self
employee_fixture.add(4, name='Sue Ecide-Risk', company=company_fixture.fk(2), manager=employee_fixture.fk(3))
# OneToOne
employee_history_fixture.add(3, employee=employee_fixture.o2o(3), date_joined='2003-03-15')
employee_history_fixture.add(4, employee=employee_fixture.o2o(4), date_joined='2006-08-07')
