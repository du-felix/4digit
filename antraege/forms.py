from django import forms
from .models import Antrag, Anfrage

class AntragForm(forms.ModelForm):
    class Meta:
        model = Antrag
        fields = ['title', 'grund', 'anfangsdatum', 'enddatum']