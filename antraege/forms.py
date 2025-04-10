
from django import forms
from .models import Antrag, Anfrage, Lehrer, Fach
from django.forms import formset_factory
from adminview.views import validate_afra_email


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
    lehrer = forms.ModelChoiceField(queryset=Lehrer.objects.all(), label="Lehrer", widget=forms.Select(attrs={'style': 'width: 200px'}))
    fach = forms.ModelChoiceField(queryset=Fach.objects.all(), label="Fach", widget=forms.Select(attrs={'style': 'width: 200px'}))
    datum = forms.DateField(label="Datum", widget=forms.DateInput(attrs={'type': 'date'}))

UnterrichtFormSet = formset_factory(Unterricht, extra=1)