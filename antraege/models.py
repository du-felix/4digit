from django.db import models
from django.conf import settings

class Antrag(models.Model):
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_DECLINED, 'Declined'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    grund = models.TextField()
    erstellt_am = models.DateTimeField(auto_now_add=True)
    anfangsdatum = models.DateField()
    enddatum = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS,
    )

    def __str__(self):
        return self.user.first_name, self.titel
    
class Anfrage(models.Model):
    antrag = models.ForeignKey(Antrag, on_delete=models.CASCADE)