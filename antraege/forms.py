
from django import forms
from .models import Antrag, Anfrage
from django.forms import formset_factory


class AntragForm(forms.ModelForm):#
    class Meta:
        model = Antrag
        fields = ['titel', 'grund', "klasse", 'anfangsdatum', 'enddatum']
    titel = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Kurzer Titel', 'style': 'width: 500px'}))
    grund = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'ggf. ausführliche Begründung des Antrags', 'style': 'width: 500px; height: 150px;'}))
    klasse = forms.CharField(max_length=3, widget=forms.TextInput(attrs={'style': 'width: 500px;'}))
    anfangsdatum = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'style': 'width: 500px'}))
    enddatum = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'style': 'width: 500px'}))
class Unterricht(forms.Form):
    lehrer_email = forms.EmailField(label="Lehrer-Email",widget=forms.TextInput(attrs={'placeholder': 'Email-Adresse des Lehrers'}))
    fach = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Betroffenes Fach'}))
    datum = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

UnterrichtFormSet = formset_factory(Unterricht, extra=1)