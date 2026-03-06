from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from .forms import UserEditForm, add_lehrer_Form
from users.forms import Sign_Up_Form
from users.models import CustomUser
from django.db.models import Q
from django.http import JsonResponse
from antraege.models import Lehrer
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string


User = get_user_model()

def staff_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def validate_afra_email(email):
    if not email.endswith('@afra.lernsax.de'):
        raise ValidationError('Nur E-Mail-Adressen, die mit "@afra.lernsax.de" enden, sind zulässig.')
    return email

@staff_required
def adminview(request, user_id=None):
    search_query = request.GET.get('q', '')

    if search_query:
        users = User.objects.filter(
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        ).order_by('-is_staff', 'email')
    else:
        users = User.objects.all().order_by('-is_staff', 'email')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user_data = []
        for user in users:
            user_data.append({
                'id': user.id,
                'email': user.email,
                'name': f"{user.first_name} {user.last_name}",
                'is_staff': user.is_staff,
            })
        return JsonResponse({'users': user_data})

    if request.method == 'POST' and 'delete_user' in request.POST:
        user_id_to_delete = request.POST.get('delete_user')
        user_to_delete = get_object_or_404(User, id=user_id_to_delete)
        user_to_delete.delete()
        messages.success(request, f'Benutzer {user_to_delete.email} erfolgreich gelöscht')
        return redirect('adminview-home')

    if request.method == 'POST' and 'action' in request.POST:
        selected_users = request.POST.getlist('selected_users')
        action = request.POST.get('action')

        if not selected_users:
            messages.error(request, 'Keine Benutzer ausgewählt')
            return redirect('adminview-home')

        users = CustomUser.objects.filter(id__in=selected_users)

        if action == 'delete':
            users.delete()
            messages.success(request, f'{len(selected_users)} Benutzer wurden gelöscht')
        return redirect('adminview-home')

    context = {
        'users': users,
        'edit_user': None,
        'search_query': search_query,
        'button_url': reverse('adminview-csv'),
    }

    return render(request, 'adminview/home.html', context)

@staff_required
def adding(request):
    if request.method == 'POST':
        form = Sign_Up_Form(request.POST)
        if form.is_valid():
            try:
                validate_afra_email(form.cleaned_data['email'])
                form.save()
                return redirect('adminview-home')
            except ValidationError as e:
                form.add_error('email', e)
    else:
        form = Sign_Up_Form()

    return render(request, 'adminview/add_user.html', {'form': form})

@staff_required
def edit_user(request, user_id=None):
    if user_id:
        edit_user = get_object_or_404(User, id=user_id)
        if request.method == 'POST':
            form = UserEditForm(request.POST, instance=edit_user)
            if form.is_valid():
                try:
                    validate_afra_email(form.cleaned_data['email'])
                    form.save()
                    messages.success(request, f"User {edit_user.email} updated successfully")
                    return redirect('adminview-home')
                except ValidationError as e:
                    form.add_error('email', e)
        else:
            form = UserEditForm(instance=edit_user)
    else:
        edit_user = None
        form = Sign_Up_Form()
    return render(request, 'adminview/edit_user.html', {'form': form, 'edit_user': edit_user})

@staff_required
def csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']

            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Bitte eine CSV-Datei hochladen.')
                return redirect('adminview-csv')

            try:
                import io
                import csv as csv_module

                csv_data = csv_file.read().decode('utf-8')
                io_string = io.StringIO(csv_data)
                reader = csv_module.reader(io_string, delimiter=';')

                success_count = 0
                error_count = 0
                errors = []

                for row in reader:
                    try:
                        if len(row) >= 3:
                            email = row[1].strip()
                            name_parts = row[2].strip().split(' ', 1)
                            first_name = name_parts[0]
                            last_name = name_parts[1] if len(name_parts) > 1 else ''

                            try:
                                validate_afra_email(email)
                            except ValidationError as e:
                                errors.append(f"Ungültige E-Mail ({email}): {str(e)}")
                                error_count += 1
                                continue

                            if not CustomUser.objects.filter(email=email).exists():
                                password = get_random_string(10)

                                user = CustomUser(
                                    email=email,
                                    first_name=first_name,
                                    last_name=last_name,
                                    is_active=False,
                                )
                                user.set_password(password)
                                user.save()

                                send_mail(
                                    subject='Dein neuer Account für Freistellungen',
                                    message=(
                                        f'Dein Account wurde erstellt.\n\n'
                                        f'Dein Initialpasswort lautet: {password}\n\n'
                                        f'Nach dem ersten Login wirst du aufgefordert, dein Passwort zu ändern.'
                                    ),
                                    from_email=settings.DEFAULT_FROM_EMAIL,
                                    recipient_list=[email],
                                    fail_silently=True,
                                )
                                success_count += 1
                            else:
                                errors.append(f"Benutzer mit E-Mail {email} existiert bereits.")
                                error_count += 1
                        else:
                            # Do NOT include raw row data in user-facing messages
                            errors.append("Eine Zeile hat zu wenige Spalten und wurde übersprungen.")
                            error_count += 1
                    except Exception:
                        errors.append("Eine Zeile konnte nicht verarbeitet werden.")
                        error_count += 1

                if success_count > 0:
                    messages.success(request, f'{success_count} Benutzer erfolgreich erstellt.')
                if error_count > 0:
                    messages.warning(request, f'{error_count} Zeilen konnten nicht verarbeitet werden.')
                    for error in errors[:10]:
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... und {len(errors) - 10} weitere Fehler.")

            except Exception:
                messages.error(request, 'Fehler beim Verarbeiten der Datei. Bitte Format prüfen.')

            return redirect('adminview-home')

    return render(request, 'adminview/csv.html')

@staff_required
def lehrer(request, lehrer_id=None):
    search_query = request.GET.get('q', '')
    if search_query:
        lehrers = Lehrer.objects.filter(
            Q(email__icontains=search_query) |
            Q(name__icontains=search_query)
        ).order_by('-secretariat', '-principal', 'email')
    else:
        lehrers = Lehrer.objects.all().order_by('-secretariat', '-principal', 'email')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        lehrer_data = []
        for l in lehrers:
            lehrer_data.append({
                'id': l.id,
                'email': l.email,
                'name': l.name,
            })
        return JsonResponse({'lehrers': lehrer_data})

    if request.method == 'POST' and 'delete_lehrer' in request.POST:
        lehrer_id_to_delete = request.POST.get('delete_lehrer')
        lehrer_to_delete = get_object_or_404(Lehrer, id=lehrer_id_to_delete)
        lehrer_to_delete.delete()
        messages.success(request, f'Lehrer {lehrer_to_delete.email} erfolgreich gelöscht')
        return redirect('lehrer')

    if request.method == 'POST' and 'action' in request.POST:
        selected_lehrers = request.POST.getlist('selected_lehrers')
        action = request.POST.get('action')

        if not selected_lehrers:
            messages.error(request, 'Keine Lehrer ausgewählt')
            return redirect('lehrer')

        qs = Lehrer.objects.filter(id__in=selected_lehrers)

        if action == 'delete':
            qs.delete()
            messages.success(request, f'{len(selected_lehrers)} Lehrer wurden gelöscht')
        return redirect('lehrer')

    context = {
        'lehrers': lehrers,
        'edit_lehrer': None,
        'search_query': search_query,
        'button_url': reverse('lehrer_csv'),
    }

    return render(request, 'adminview/lehrer.html', context)

@staff_required
def add_lehrer(request):
    if request.method == 'POST':
        form = add_lehrer_Form(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lehrer')
    else:
        form = add_lehrer_Form()

    return render(request, 'adminview/add_lehrer.html', {'form': form})

@staff_required
def edit_lehrer(request, lehrer_id=None):
    if lehrer_id is not None:
        edit_lehrer_obj = get_object_or_404(Lehrer, id=lehrer_id)
        if request.method == 'POST':
            form = add_lehrer_Form(request.POST, instance=edit_lehrer_obj)
            if form.is_valid():
                lehrer_instance = form.save(commit=False)
                lehrer_instance.principal = 'is_principal' in request.POST
                lehrer_instance.secretariat = 'is_secretariat' in request.POST
                lehrer_instance.save()
                messages.success(request, f"Lehrer {lehrer_instance.email} erfolgreich aktualisiert")
                return redirect('lehrer')
        else:
            form = add_lehrer_Form(instance=edit_lehrer_obj)
    else:
        edit_lehrer_obj = None
        form = add_lehrer_Form()

    return render(request, 'adminview/edit_lehrer.html', {'form': form, 'edit_lehrer': edit_lehrer_obj})
@staff_required
def lehrer_csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']

            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Bitte eine CSV-Datei hochladen.')
                return redirect('lehrer_csv')

            try:
                import io
                import csv as csv_module

                csv_data = csv_file.read().decode('utf-8')
                io_string = io.StringIO(csv_data)
                reader = csv_module.reader(io_string, delimiter=';')

                success_count = 0
                error_count = 0
                errors = []

                for row in reader:
                    try:
                        if len(row) >= 3:
                            email = row[1].strip()
                            name = row[2].strip()

                            if not Lehrer.objects.filter(email=email).exists():
                                Lehrer.objects.create(email=email, name=name)
                                success_count += 1
                            else:
                                errors.append(f"Lehrer mit E-Mail {email} existiert bereits.")
                                error_count += 1
                        else:
                            errors.append("Eine Zeile hat zu wenige Spalten und wurde übersprungen.")
                            error_count += 1
                    except Exception:
                        errors.append("Eine Zeile konnte nicht verarbeitet werden.")
                        error_count += 1

                if success_count > 0:
                    messages.success(request, f'{success_count} Lehrer erfolgreich erstellt.')
                if error_count > 0:
                    messages.warning(request, f'{error_count} Zeilen konnten nicht verarbeitet werden.')
                    for error in errors[:10]:
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... und {len(errors) - 10} weitere Fehler.")

            except Exception:
                messages.error(request, 'Fehler beim Verarbeiten der Datei. Bitte Format prüfen.')

            return redirect('lehrer')

    return render(request, 'adminview/lehrer_csv.html')
