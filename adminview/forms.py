from django import forms
from django.contrib.auth import get_user_model
from antraege.models import Lehrer

User = get_user_model()


class CreateUserForm(forms.ModelForm):
    """
    Lightweight form used by staff to create a new student account.
    No password fields — an activation link is emailed to the student
    so they set their own password.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Vorname',
            'last_name': 'Nachname',
            'email': 'E-Mail-Adresse',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
        }


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'is_staff']
        labels = {
            'email': 'E-Mail-Adresse',
            'first_name': 'Vorname',
            'last_name': 'Nachname',
            'is_staff': 'Administrator',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
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