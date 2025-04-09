from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as lg
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from .models import CustomUser

def login(request):

    if request.method == "POST":
        email = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_staff:
                lg(request, user)
                messages.success(request, "Login successful!")

                return redirect("adminview-home")  # Redirect to staff dashboard
            else:
                lg(request, user)
                return redirect("home")  
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "users/login.html")  # Render the login page

def signup(request):
    if request.method == 'POST':
        vorname = request.POST.get('vorname')
        nachname = request.POST.get('nachname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        geburtsdatum = request.POST.get('geburtsdatum')
        
        try:
            existing_user = CustomUser.objects.get(email=email)
            messages.error(request, "Email already exists.")
            if not existing_user.is_active:
                messages.info(request, "Du hast bereits ein Konto, aber es ist noch nicht aktiviert. Wir haben dir eine neue Email geschickt.")
                # Optionally, resend the activation email
                token = default_token_generator.make_token(existing_user)
                activation_url = request.build_absolute_uri(
                    reverse('activate', kwargs={'uid': existing_user.pk, 'token': token})
                )
                send_mail(
                    'Activate your account',
                    f'Hi {vorname}, bitte klicke auf diesen Link um deinen Account zu bestätigen: {activation_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                return render(request, "users/signup_complete.html", {"activated": False})
            else:
                messages.info(request, "Du hast bereits ein Konto. Bitte logge dich ein.")
                return redirect('login')
        except CustomUser.DoesNotExist:
            user = CustomUser.objects.create_user(
                username=email,
                first_name=vorname.capitalize(),
                last_name=nachname.capitalize(),
                email=email,
                password=password,
                #birth_date=geburtsdatum
            )
            user.is_active = False
            user.save()
            token = default_token_generator.make_token(user)
            activation_url = request.build_absolute_uri(
                reverse('activate', kwargs={'uid': user.pk, 'token': token})
            )
            send_mail(
                'Activate your account',
                f'Hi {vorname}, bitte klicke auf diesen Link um deinen Account zu bestätigen: {activation_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )
            print("passed")
            return render(request, "users/signup_complete.html", {"activated": False})
    else:
        return render(request, 'users/signup.html')

def activate(request, uid, token):
    user = get_object_or_404(CustomUser, pk=uid)
    if default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Dein Account wurde erfolgreich aktiviert! Du kannst dich jetzt einloggen.")
        return render(request, "users/signup_complete.html", {"activated": True})
    else:
        messages.error(request, "Activation Link ist ungültig oder abgelaufen, registriere dich bitte ")
        return redirect('signup')