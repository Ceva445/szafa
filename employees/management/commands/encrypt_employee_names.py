from django.core.management.base import BaseCommand
from employees.models import Employee
from szafa.crypto import encrypt_value


class Command(BaseCommand):

    help = "Encrypt employee names"

    def handle(self, *args, **kwargs):

        for emp in Employee.objects.all():

            if not emp._first_name.startswith("gAAAA"):
                emp._first_name = encrypt_value(emp._first_name)

            if not emp._last_name.startswith("gAAAA"):
                emp._last_name = encrypt_value(emp._last_name)

            emp.save(update_fields=["_first_name", "_last_name"])

        self.stdout.write(self.style.SUCCESS("Encryption completed"))