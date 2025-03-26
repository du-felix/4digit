
from django import forms
from .models import Antrag, Anfrage
from django.forms import formset_factory


class AntragForm(forms.ModelForm):#
    class Meta:
        model = Antrag
        fields = ['titel', 'grund', "klasse", 'anfangsdatum', 'enddatum']
    anfangsdatum = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    enddatum = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
class Unterricht(forms.Form):
    lehrer_email = forms.EmailField(widget=forms.TextInput(attrs={'placeholder': 'Email des Lehrers'}))
    fach = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Betroffenes Fach'}))
    datum = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

UnterrichtFormSet = formset_factory(Unterricht, extra=1)