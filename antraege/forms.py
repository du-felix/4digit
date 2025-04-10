
from django import forms
from .models import Antrag, Anfrage, Lehrer, Fach
from django.forms import formset_factory
from adminview.views import validate_afra_email


class AntragForm(forms.ModelForm):
    class Meta:
        model = Antrag
        fields = ['titel', 'grund', "klasse", 'anfangsdatum', 'enddatum', 'im', 'gm']
        widgets = {
            'klasse': forms.Select(attrs={'style': 'width: 500px;'})
        }
    titel = forms.CharField(required=True,max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Kurzer Titel', 'style': 'width: 500px'}))
    grund = forms.CharField(required=True,widget=forms.Textarea(attrs={'placeholder': 'ggf. ausführliche Begründung des Antrags', 'style': 'width: 500px; height: 150px;'}))
    anfangsdatum = forms.DateField(required=True,widget=forms.DateInput(attrs={'type': 'date', 'style': 'width: 500px'}))
    enddatum = forms.DateField(required=True,widget=forms.DateInput(attrs={'type': 'date', 'style': 'width: 500px'}))
    im = forms.ModelChoiceField(required=True,queryset=Lehrer.objects.all(), label="IM", widget=forms.Select(attrs={'style': 'width: 500px'}))
    gm = forms.ModelChoiceField(required=True,queryset=Lehrer.objects.all(), label="GM", widget=forms.Select(attrs={'style': 'width: 500px'}))

class Unterricht(forms.Form):
    lehrer = forms.ModelChoiceField(required=True,queryset=Lehrer.objects.all(), label="Lehrer", widget=forms.Select(attrs={'style': 'width: 500px'}))
    fach = forms.ModelChoiceField(required=True,queryset=Fach.objects.all(), label="Fach", widget=forms.Select(attrs={'style': 'width: 500px'}))
    datum = forms.DateField(required=True,label="Datum", widget=forms.DateInput(attrs={'type': 'date'}))

UnterrichtFormSet = formset_factory(Unterricht, extra=1)