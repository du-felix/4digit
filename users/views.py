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
from django.contrib.auth.forms import SetPasswordForm

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
            try:
                user = CustomUser.objects.get(email=email)
                if user.password == password and not user.is_active:
                    token = default_token_generator.make_token(user)
                    return render(request, "users/activate.html", {"uid": user.pk, "token": token})
                else:
                    messages.error(request, "Invalid password.")
            except CustomUser.DoesNotExist:
                messages.error(request, "Invalid email.")


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
        password = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password == password2:
            user.set_password(password)
            user.is_active = True
            user.save()

            return render(request, "users/signup_complete.html", {"activated": True})
        else:
            messages.error(request, "Passwörter stimmen nicht überein.")
            return render(request, "users/activate.html", {"uid": uid, "token": token})
    else:
        messages.error(request, "Es ist ein Fehler aufgetreten.")
        return redirect('login')
    
def edit_password(request, uid, token):
    user = get_object_or_404(CustomUser, pk=uid)

    if default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Passwort erfolgreich geändert!")
                return redirect('login')
            else:
                messages.error(request, "Passwort konnte nicht geändert werden.")
                form = SetPasswordForm(user, request.POST)
                return render(request, "users/reset_password.html", {"form": form})
        else:
            form = SetPasswordForm(user)
        return render(request, "users/reset_password.html", {"form": form})
    else:
        messages.error(request, "Activation Link ist ungültig oder abgelaufen, fordere einen neuen an. ")
        return redirect('login')

def activate_account(request):
    if request.method == "POST":
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        user = request.user

        if password == password2:
            user.set_password(password)
            user.is_active = True
            user.save()
            messages.success(request, "Passwort erfolgreich geändert!")
            return redirect('login')
        else:
            messages.error(request, "Passwörter stimmen nicht überein.")
            render(request, "users/activate.html", {"uid": request.user.pk})

def get_link(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = CustomUser.objects.get(email=email)
            if not user.is_active:
                password = user.password
                send_mail(
                    'Initialpasswort für Freistellungen',
                    f'Hi {user.first_name}, mit diesem Initialpasswort kannst du dich einloggen: {password}\n Bitte ändere es nach dem ersten Login.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email], fail_silently=False
                )
                messages.error(request, "Dein Konto wurde noch nicht aktiviert. Wir haben dir eine Mail mit deinem Initialpasswort geschickt. Damit kannst du dich einloggen und dir ein eigenes Passwort erstellen.")
                return redirect('login')
            else:
                token = default_token_generator.make_token(user)
                activation_url = request.build_absolute_uri(
                    reverse('edit_password', kwargs={'uid': user.pk, 'token': token})
                )
                send_mail(
                    'Passwort zurücksetzen',
                    f'Hi {user.first_name}, bitte klicke auf diesen Link um dein Passwort zurückzusetzen: {activation_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                messages.success(request, "Wir haben dir eine Email geschickt mit einem Link um dein Passwort zurückzusetzen.")
                return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, "Es existiert kein Konto mit dieser Email")
            return render(request, "users/get_link.html")
    return render(request, "users/get_link.html")