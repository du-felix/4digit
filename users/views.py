from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as lg
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.conf import settings
from .models import CustomUser
from django.contrib.auth.forms import SetPasswordForm
from django.http import HttpResponse
from antraege.mailer import send_mail_logged


def login(request):
    if request.method == "POST":
        email = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            lg(request, user)
            if user.is_staff:
                return redirect("adminview-home")
            return redirect("home")
        messages.error(request, "Ungültige Anmeldedaten.")

    return render(request, "users/login.html")


def activate(request, uid, token):
    user = get_object_or_404_custom(CustomUser, pk=uid)
    if user is None:
        messages.error(request, "Ungültiger Aktivierungslink.")
        return redirect('login')

    if not default_token_generator.check_token(user, token):
        messages.error(request, "Der Aktivierungslink ist ungültig oder abgelaufen.")
        return redirect('login')

    # Only process password on POST — prevents GET-request activation (None==None bug)
    if request.method == 'POST':
        password = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not password:
            messages.error(request, "Passwort darf nicht leer sein.")
            return render(request, "users/activate.html", {"uid": uid, "token": token})

        if password != password2:
            messages.error(request, "Passwörter stimmen nicht überein.")
            return render(request, "users/activate.html", {"uid": uid, "token": token})

        user.set_password(password)
        user.is_active = True
        user.save()
        return render(request, "users/signup_complete.html", {"activated": True})

    # GET: just show the form
    return render(request, "users/activate.html", {"uid": uid, "token": token})


def get_object_or_404_custom(model, **kwargs):
    """Returns None instead of raising Http404, for flows that need custom error handling."""
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


def edit_password(request, uid, token):
    user = get_object_or_404_custom(CustomUser, pk=uid)
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Der Link ist ungültig oder abgelaufen. Bitte fordere einen neuen an.")
        return redirect('login')

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Passwort erfolgreich geändert!")
            return redirect('login')
        messages.error(request, "Passwort konnte nicht geändert werden.")
        return render(request, "users/reset_password.html", {"form": form})

    form = SetPasswordForm(user)
    return render(request, "users/reset_password.html", {"form": form})


@login_required(login_url='login')
def activate_account(request):
    """Password-change flow for already-authenticated inactive users."""
    if request.method == "POST":
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        user = request.user

        if not password:
            messages.error(request, "Passwort darf nicht leer sein.")
            return render(request, "users/activate.html", {"uid": user.pk})

        if password == password2:
            user.set_password(password)
            user.is_active = True
            user.save()
            messages.success(request, "Passwort erfolgreich geändert!")
            return redirect('login')

        messages.error(request, "Passwörter stimmen nicht überein.")
        return render(request, "users/activate.html", {"uid": user.pk})

    return render(request, "users/activate.html", {"uid": request.user.pk})


def get_link(request):
    if request.method == "POST":
        email = request.POST.get("email")
        # Uniform message in ALL branches (user missing / inactive / active) so
        # the endpoint can't be used to enumerate which emails have accounts.
        generic_message = "Wenn ein Konto mit dieser E-Mail existiert, wurde eine E-Mail verschickt."
        try:
            user = CustomUser.objects.get(email=email)

            if not user.is_active:
                token = default_token_generator.make_token(user)
                activation_url = request.build_absolute_uri(
                    reverse('activate', kwargs={'uid': user.pk, 'token': token})
                )
                send_mail_logged(
                    subject='Account aktivieren – Freistellungen',
                    body=(
                        f'Hi {user.first_name},\n\n'
                        f'Dein Account wurde noch nicht aktiviert. '
                        f'Klicke auf folgenden Link um ein Passwort festzulegen:\n\n'
                        f'{activation_url}\n\n'
                        f'Der Link ist für eine begrenzte Zeit gültig.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipients=[email],
                )
            else:
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    reverse('edit_password', kwargs={'uid': user.pk, 'token': token})
                )
                send_mail_logged(
                    subject='Passwort zurücksetzen',
                    body=(
                        f'Hi {user.first_name},\n\n'
                        f'Klicke auf folgenden Link um dein Passwort zurückzusetzen:\n\n'
                        f'{reset_url}'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipients=[email],
                )
        except CustomUser.DoesNotExist:
            pass

        messages.success(request, generic_message)
        return redirect('login')

    return render(request, "users/get_link.html")


# signup view intentionally left without URL registration (route is commented out in urls.py)
def signup(request):
    return redirect('login')
