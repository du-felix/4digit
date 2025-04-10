from django import forms
from django.contrib.auth import get_user_model
from antraege.models import Lehrer

User = get_user_model()

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            # 'birth_date', 
            'is_staff'
            ]
        labels = {
        'email': 'E-Mail-Adresse',
        'first_name': 'Vorname',
        'last_name': 'Nachname',
        #'birth_date': 'Geburtsdatum',
        'is_staff': 'Administrator',
    }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            #'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
class add_lehrer_Form(forms.ModelForm):
    class Meta:
        model = Lehrer
        fields = [
            'email',
            'name',
            ]
        labels = {
        'email': 'E-Mail-Adresse',
        'name': 'Name',
    }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }