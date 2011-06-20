# The fixtures in this file will be loaded during a syncdb operation.
from class_fixtures.models import Fixture
from class_fixtures.tests.models import Party, Politician

initial_party = Fixture(Party)
initial_politician = Fixture(Politician)
initial_party.add(2, name="The People's Technocratic Party of Vinnland")
initial_politician.add(2, name="Petrus T. Ratajczyk", party=initial_party.fk(2))
