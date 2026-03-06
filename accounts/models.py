from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    can_view_real_employee_names = models.BooleanField(
        default=False,
        help_text="User can see decrypted employee names"
    )

    def __str__(self):
        return self.username