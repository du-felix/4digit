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

    KLASSE_CHOICES = [
        ("7", "7"),
        ("8", "8"),
        ("9a", "9a"),
        ("9b", "9b"),
        ("9c", "9c"),
        ("10a", "10a"),
        ("10b", "10b"),
        ("10c", "10c"),
        ("11", "11"),
        ("12", "12"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    titel = models.CharField(max_length=50)
    grund = models.TextField()
    klasse = models.CharField(max_length=3, choices=KLASSE_CHOICES)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    anfangsdatum = models.DateField()
    enddatum = models.DateField()
    status = models.CharField(
        max_length=100,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS,
    )
    

    def __str__(self):
        return self.user.first_name, self.titel
    


class Anfrage(models.Model):
    NOT_RESPONDED = 'not_responded'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'

    RESPONSE_CHOICES = [
        (NOT_RESPONDED, 'Noch nicht geantwortet'),
        (ACCEPTED, 'Genehmigt'),
        (DECLINED, 'Abgelehnt'),
    ]
    antrag = models.ForeignKey(Antrag, on_delete=models.CASCADE)
    # Momentan wird der Antragssteller die Emaiil eingeben. Es gibt keine klare Zuodnung von Lehrer und Mail.
    email = models.EmailField()
    @property
    def name(self):
        local_part = self.email.split('@')[0]
        return " ".join(word.capitalize() for word in local_part.split('.'))
    unterricht = models.TextField()
    gm = models.EmailField(null=True, blank=True)
    im = models.EmailField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    response = models.CharField(
        max_length=100,
        choices=RESPONSE_CHOICES,
        default=NOT_RESPONDED,
    )
    reason = models.TextField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    is_principle = models.BooleanField(default=False, blank=True)
    token = models.CharField(max_length=64, unique=True, blank=True, null=True)

class Fach(models.Model):
    name = models.CharField(max_length=100)
    kuerzel = models.CharField(max_length=10, unique=True)
    def __str__(self):
        return self.name
class Lehrer(models.Model):
    email = models.EmailField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    principal = models.BooleanField(default=False, blank=True)
    secretariat = models.BooleanField(default=False, blank=True)
    def __str__(self):
        return self.name

class Zaehler(models.Model):
    schueler = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lehrer = models.ForeignKey(Lehrer, on_delete=models.CASCADE)
    fach = models.ForeignKey(Fach, on_delete=models.CASCADE)
    zaehler = models.IntegerField(default=0)
    temp = models.IntegerField(default=0)