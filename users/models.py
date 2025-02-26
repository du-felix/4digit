from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Extra fields
    birth_date = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.email:
            self.username = self.email  # Automatically set username to email
        super().save(*args, **kwargs)

