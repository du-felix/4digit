from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class Sign_Up_Form(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        # Notice we exclude the username field because it will be auto-assigned.
        fields = ('email', 'birth_date', 'password1', 'password2')
