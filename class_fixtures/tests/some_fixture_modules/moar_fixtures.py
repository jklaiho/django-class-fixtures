from class_fixtures.models import Fixture
from class_fixtures.tests.models import *

membership_fixture = Fixture(Membership)
band_fixture = Fixture(Band)
musician_fixture = Fixture(Musician)

band_fixture.add(6, name="R.A.M.")

musician_fixture.add(7, name="Michael Skype")

# Keyword-based FK target lookup
membership_fixture.add(9,
    musician = musician_fixture.fk(7),
    band = band_fixture.fk(6),
    date_joined = '1980-05-19',
    instrument = "Voice",
)