from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class Sign_Up_Form(UserCreationForm):

    email = forms.EmailField(required=True)
    #birth_date = forms.DateField(
        #widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'DD.MM.YYYY'}),
        #input_formats=['%Y-%m-%d'],  # This goes to DateField, not DateInput
        #required=True
    #)

    class Meta:
        model = CustomUser
        # Notice we exclude the username field because it will be auto-assigned.
        fields = ("first_name",
                  "last_name",
                  'email',
                  #'birth_date',
                  'password1',
                  'password2')
        labels = {
            'first_name': 'Vorname',
            'last_name': 'Nachname',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Explicitly override password field labels here
        self.fields['email'].label = 'E-Mail-Adresse'
        #self.fields['birth_date'].label = 'Geburtsdatum'
        self.fields['password1'].label = 'Passwort'
        self.fields['password2'].label = 'Passwort bestätigen'
        self.fields['password1'].help_text = '<br>Das Passwort muss mindestens 8 Zeichen enthalten.<br>Es darf nicht nur aus Zahlen bestehen.'
        self.fields['password2'].help_text = '<br>Bitte das Passwort zur Bestätigung erneut eingeben.'