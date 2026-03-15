
from django import forms
from .models import Antrag, Anfrage, Lehrer, Fach
from django.forms import formset_factory


class AntragForm(forms.ModelForm):
    class Meta:
        model = Antrag
        fields = ['titel', 'grund', "klasse", 'anfangsdatum','anfangszeit', 'enddatum', 'endzeit', 'im', 'gm']
        widgets = {
            'klasse': forms.Select(attrs={'style': 'width: 500px;'})
        }
    titel = forms.CharField(required=True,max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Kurzer Titel', 'style': 'width: 500px'}))
    grund = forms.CharField(required=True,widget=forms.Textarea(attrs={'placeholder': 'ggf. ausführliche Begründung des Antrags', 'style': 'width: 500px; height: 150px;'}))
    anfangsdatum = forms.DateField(required=True,widget=forms.DateInput(attrs={'type': 'date', 'style': 'width: 500px'}))
    anfangszeit = forms.TimeField(required=True,widget=forms.TimeInput(attrs={'type': 'time', 'style': 'width: 500px'}))    
    enddatum = forms.DateField(required=True,widget=forms.DateInput(attrs={'type': 'date', 'style': 'width: 500px'}))
    endzeit = forms.TimeField(required=True,widget=forms.TimeInput(attrs={'type': 'time', 'style': 'width: 500px'}))
    im = forms.ModelChoiceField(required=True, queryset=Lehrer.objects.filter(is_im=True).order_by('name'), label="IM", widget=forms.Select(attrs={'style': 'width: 500px'}))
    gm = forms.ModelChoiceField(required=True, queryset=Lehrer.objects.filter(is_gm=True).order_by('name'), label="GM", widget=forms.Select(attrs={'style': 'width: 500px'}))

class Unterricht(forms.Form):
    DS_CHOICES = [
        ("1. DS", "1. DS"),
        ("2. DS", "2. DS"),
        ("3. DS", "3. DS"),
        ("4. DS", "4. DS"),
        ("5. DS", "5. DS"),
        ("6. DS", "6. DS"),
        ("andere", "Andere (bitte im Grund angeben)"),
    ]
    lehrer = forms.ModelChoiceField(required=True,queryset=Lehrer.objects.all().order_by('name'), label="Lehrer", widget=forms.Select(attrs={'style': 'width: 500px'}))
    fach = forms.ModelChoiceField(required=True,queryset=Fach.objects.all().order_by('name'), label="Fach", widget=forms.Select(attrs={'style': 'width: 500px'}))
    datum = forms.DateField(required=True,label="Datum", widget=forms.DateInput(attrs={'type': 'date'}))
    ds_zeit = forms.ChoiceField(required=True, choices=DS_CHOICES, label="Fehlende Doppelstunde", widget=forms.Select(attrs={'style': 'width: 500px'}))

UnterrichtFormSet = formset_factory(Unterricht, extra=1)

YES_NO = (("ja", "Ja"), ("nein", "Nein"))
class TwoStepForm(forms.Form):
    first_question  = forms.ChoiceField(
        choices=YES_NO,
        widget=forms.RadioSelect
    )
    second_question = forms.ChoiceField(
        label="Liegt die Bestätigung der Eltern vor?",
        choices=YES_NO,
        widget=forms.RadioSelect,
        required=False       # always optional at field-declaration time
    )

    def clean(self):
        cleaned = super().clean()
        # if they said “yes” to the first, they must answer the second
        if cleaned.get("first_question") == "ja" and not cleaned.get("second_question"):
            self.add_error("second_question", "This field is required when you answer Yes above.")
        return cleaned
    
class YesNoForm(forms.Form):
    agree = forms.BooleanField(
        label="Yes / No",
        required=False,  # unchecked → False; checked → True
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input", 
            "role": "switch"
        })
    )
