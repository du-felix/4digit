from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class Sign_Up_Form(UserCreationForm):

    email = forms.EmailField(required=True)
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'DD.MM.YYYY'}),
        input_formats=['%Y-%m-%d'],  # This goes to DateField, not DateInput
        required=True
    )

    class Meta:
        model = CustomUser
        # Notice we exclude the username field because it will be auto-assigned.
        fields = ("first_name", "last_name", 'email', 'birth_date', 'password1', 'password2')
