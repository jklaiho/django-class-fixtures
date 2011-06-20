from class_fixtures.models import Fixture
from class_fixtures.tests.models import Company, Employee, EmployeeHistory

company_fixture = Fixture(Company)
employee_fixture = Fixture(Employee)
employee_history_fixture = Fixture(EmployeeHistory)

company_fixture.add(3, name='Dewey, Cheatem & Howe')
employee_fixture.add(5, name='Sly M. Ball', company=company_fixture.fk(3))
employee_fixture.add(6, name='Mei Ting', company=company_fixture.fk(3), manager=employee_fixture.fk(5))
employee_history_fixture.add(5, employee=employee_fixture.o2o(5), date_joined='2000-11-03')
employee_history_fixture.add(6, employee=employee_fixture.o2o(6), date_joined='1985-12-28')
