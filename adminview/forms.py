from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'birth_date', 'is_staff']
        labels = {
        'email': 'E-Mail-Adresse',
        'first_name': 'Vorname',
        'last_name': 'Nachname',
        'birth_date': 'Geburtsdatum',
        'is_staff': 'Administrator',
    }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }