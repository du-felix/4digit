from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from .forms import UserEditForm, CreateUserForm, add_lehrer_Form, AddFachForm
from users.models import CustomUser
from django.db.models import Count, Q, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
import io
import csv as csv_module
from antraege.models import Lehrer, Antrag, Anfrage, Fach
from antraege.validators import validate_afra_email
from antraege.mailer import send_mail_logged
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta


User = get_user_model()


def _decode_csv_content(raw_bytes):
    """Decode uploaded CSV bytes using common encodings used by school exports."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(
        "Die Datei konnte nicht gelesen werden. Bitte als UTF-8 oder cp1252/latin1 speichern."
    )


def _parse_student_csv(csv_data):
    """
    Parse student CSV rows with strict 3-column format:
    ignored;email;full name
    """
    reader = csv_module.reader(io.StringIO(csv_data), delimiter=';')
    parsed_rows = []
    errors = []

    for line_number, row in enumerate(reader, start=1):
        if not row or all(not cell.strip() for cell in row):
            continue

        if len(row) != 3:
            errors.append(
                f"Zeile {line_number}: Es werden genau 3 Spalten erwartet "
                "(Loginname;E-Mail;Vollständiger Name)."
            )
            continue

        _ignored_login, email, full_name = [cell.strip() for cell in row]
        if not email or not full_name:
            errors.append(
                f"Zeile {line_number}: E-Mail und vollständiger Name müssen ausgefüllt sein "
                "(Spalten 2 und 3)."
            )
            continue

        try:
            validate_afra_email(email)
        except ValidationError as exc:
            errors.append(f"Zeile {line_number}: Ungültige E-Mail ({email}): {str(exc)}")
            continue

        name_parts = full_name.split(None, 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        parsed_rows.append(
            {
                "line_number": line_number,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            }
        )

    return parsed_rows, errors


def _send_activation_email(request, user):
    """Generate a one-time activation link and email it to the user."""
    token = default_token_generator.make_token(user)
    url = request.build_absolute_uri(
        reverse('activate', kwargs={'uid': user.pk, 'token': token})
    )
    if url.startswith('http://'):
        url = 'https://' + url[7:]
    send_mail_logged(
        subject='Dein Account für Freistellungen – Aktivierung',
        body=(
            f'Hallo {user.first_name},\n\n'
            f'Dein Account für das Freistellungsportal wurde angelegt. '
            f'Klicke auf folgenden Link um dein Passwort festzulegen und deinen Account zu aktivieren:\n\n'
            f'{url}\n\n'
            f'Der Link ist für eine begrenzte Zeit gültig. '
            f'Falls du keinen Account angefordert hast, kannst du diese Mail ignorieren.\n\n'
            f'BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipients=[user.email],
    )


def staff_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

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
        form = CreateUserForm(request.POST)
        if form.is_valid():
            try:
                validate_afra_email(form.cleaned_data['email'])
            except ValidationError as e:
                form.add_error('email', e)
                return render(request, 'adminview/add_user.html', {'form': form})
            user = form.save(commit=False)
            user.set_unusable_password()
            user.is_active = False
            user.save()
            _send_activation_email(request, user)
            messages.success(request, f'Benutzer {user.email} wurde angelegt. Eine Aktivierungs-E-Mail wurde versendet.')
            return redirect('adminview-home')
    else:
        form = CreateUserForm()

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
                except ValidationError as e:
                    form.add_error('email', e)
                    return render(request, 'adminview/edit_user.html', {'form': form, 'edit_user': edit_user})
                form.save()
                messages.success(request, f"User {edit_user.email} updated successfully")
                return redirect('adminview-home')
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
                csv_data = _decode_csv_content(csv_file.read())
                rows, parse_errors = _parse_student_csv(csv_data)
                if parse_errors:
                    messages.error(
                        request,
                        "Die CSV ist ungültig. Erwartetes Format je Zeile: "
                        "Loginname;E-Mail;Vollständiger Name.",
                    )
                    for error in parse_errors[:10]:
                        messages.error(request, error)
                    if len(parse_errors) > 10:
                        messages.error(request, f"... und {len(parse_errors) - 10} weitere Fehler.")
                    return redirect('adminview-csv')

                if not rows:
                    messages.error(request, 'Die CSV enthält keine verwertbaren Datensätze.')
                    return redirect('adminview-csv')

                success_count = 0
                errors = []

                for row in rows:
                    email = row["email"]

                    if CustomUser.objects.filter(email=email).exists():
                        errors.append(
                            f"Zeile {row['line_number']}: Benutzer mit E-Mail {email} existiert bereits."
                        )
                        continue

                    user = CustomUser(
                        email=email,
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        is_active=False,
                    )
                    user.set_unusable_password()
                    user.save()
                    _send_activation_email(request, user)
                    success_count += 1

                if success_count > 0:
                    messages.success(request, f'{success_count} Benutzer erfolgreich erstellt.')
                if errors:
                    messages.warning(request, f'{len(errors)} Zeilen konnten nicht verarbeitet werden.')
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
                lehrer_instance.is_im = 'is_im' in request.POST
                lehrer_instance.is_gm = 'is_gm' in request.POST
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


# ── Fächer (subjects) ─────────────────────────────────────────────────────────

@staff_required
def faecher(request):
    q = request.GET.get('q', '').strip()
    qs = Fach.objects.all().order_by('name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(kuerzel__icontains=q))

    if request.method == 'POST':
        if 'delete_fach' in request.POST:
            fach_id = request.POST.get('delete_fach')
            fach = get_object_or_404(Fach, id=fach_id)
            fach.delete()
            messages.success(request, f'Fach "{fach.name}" gelöscht.')
            return redirect('faecher')
        action = request.POST.get('action')
        if action == 'delete':
            ids = request.POST.getlist('selected_faecher')
            if ids:
                Fach.objects.filter(id__in=ids).delete()
                messages.success(request, f'{len(ids)} Fach/Fächer gelöscht.')
            return redirect('faecher')

    return render(request, 'adminview/faecher.html', {'faecher': qs, 'search_query': q})


@staff_required
def add_fach(request):
    if request.method == 'POST':
        form = AddFachForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fach erfolgreich angelegt.')
            return redirect('faecher')
    else:
        form = AddFachForm()
    return render(request, 'adminview/add_fach.html', {'form': form})


@staff_required
def edit_fach(request, fach_id):
    fach_obj = get_object_or_404(Fach, id=fach_id)
    if request.method == 'POST':
        form = AddFachForm(request.POST, instance=fach_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Fach "{fach_obj.name}" aktualisiert.')
            return redirect('faecher')
    else:
        form = AddFachForm(instance=fach_obj)
    return render(request, 'adminview/edit_fach.html', {'form': form, 'fach': fach_obj})


@staff_required
def fach_csv(request):
    if request.method == 'POST' and 'csv_file' in request.FILES:
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Bitte eine CSV-Datei hochladen.')
            return redirect('fach_csv')
        try:
            import csv as csv_module
            csv_data = csv_file.read().decode('utf-8')
            reader = csv_module.reader(io.StringIO(csv_data), delimiter=';')
            success_count = 0
            error_count = 0
            errors = []
            for row in reader:
                try:
                    if len(row) >= 2:
                        name = row[0].strip()
                        kuerzel = row[1].strip()
                        if not name or not kuerzel:
                            raise ValueError("Leere Felder")
                        if Fach.objects.filter(kuerzel=kuerzel).exists():
                            errors.append(f'Kürzel "{kuerzel}" existiert bereits.')
                            error_count += 1
                        else:
                            Fach.objects.create(name=name, kuerzel=kuerzel)
                            success_count += 1
                    else:
                        errors.append('Eine Zeile hat zu wenige Spalten.')
                        error_count += 1
                except Exception:
                    errors.append('Eine Zeile konnte nicht verarbeitet werden.')
                    error_count += 1
            if success_count:
                messages.success(request, f'{success_count} Fächer erfolgreich importiert.')
            if error_count:
                messages.warning(request, f'{error_count} Zeilen konnten nicht verarbeitet werden.')
                for e in errors[:10]:
                    messages.error(request, e)
        except Exception:
            messages.error(request, 'Fehler beim Verarbeiten der Datei.')
        return redirect('faecher')
    return render(request, 'adminview/fach_csv.html')


@staff_required
def dashboard(request):
    q = request.GET.get('q', '').strip()
    selected_filter = request.GET.get('filter', 'all').strip().lower()
    sort = request.GET.get('sort', 'newest').strip().lower()

    allowed_filters = {'all', 'antrag', 'user', 'response', 'decision'}
    if selected_filter not in allowed_filters:
        selected_filter = 'all'
    if sort not in {'newest', 'oldest'}:
        sort = 'newest'

    events = []

    for a in Antrag.objects.select_related('user').order_by('-erstellt_am'):
        text = f'{a.user.get_full_name() or a.user.email} hat einen Freistellungsantrag eingereicht'
        meta = f'"{a.titel}" · Klasse {a.klasse}'
        events.append({
            'type': 'antrag',
            'filter_key': 'antrag',
            'dot': 'dot-antrag',
            'timestamp': a.erstellt_am,
            'text': f'<strong>{a.user.get_full_name() or a.user.email}</strong> hat einen Freistellungsantrag eingereicht',
            'meta': meta,
            'search_text': f'{text.lower()} {meta.lower()}',
        })

    for r in Anfrage.objects.select_related('antrag').filter(responded_at__isnull=False).order_by('-responded_at'):
        label = 'genehmigt' if r.response == 'accepted' else 'abgelehnt'
        dot = 'dot-response' if r.response == 'accepted' else 'dot-decision'
        filter_key = 'response' if r.response == 'accepted' else 'decision'
        text = f'{r.name} hat eine Anfrage {label}'
        meta = f'Antrag: "{r.antrag.titel}"'
        events.append({
            'type': 'response',
            'filter_key': filter_key,
            'dot': dot,
            'timestamp': r.responded_at,
            'text': f'<strong>{r.name}</strong> hat eine Anfrage {label}',
            'meta': meta,
            'search_text': f'{text.lower()} {meta.lower()}',
        })

    for u in CustomUser.objects.order_by('-date_joined'):
        text = f'Neuer Benutzer angelegt: {u.get_full_name() or u.email}'
        events.append({
            'type': 'user',
            'filter_key': 'user',
            'dot': 'dot-user',
            'timestamp': u.date_joined,
            'text': f'Neuer Benutzer angelegt: <strong>{u.get_full_name() or u.email}</strong>',
            'meta': u.email,
            'search_text': f'{text.lower()} {u.email.lower()}',
        })

    total_events_all = len(events)

    if selected_filter != 'all':
        events = [event for event in events if event['filter_key'] == selected_filter]

    if q:
        q_lower = q.lower()
        events = [event for event in events if q_lower in event['search_text']]

    reverse_order = sort != 'oldest'
    events.sort(key=lambda x: x['timestamp'], reverse=reverse_order)

    paginator = Paginator(events, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop('page', None)
    pagination_query = params.urlencode()

    stats = {
        'users': CustomUser.objects.count(),
        'antraege': Antrag.objects.count(),
        'pending': Antrag.objects.filter(status=Antrag.STATUS_IN_PROGRESS).count(),
        'lehrer': Lehrer.objects.count(),
    }

    return render(request, 'adminview/dashboard.html', {
        'page_obj': page_obj,
        'stats': stats,
        'total_events': len(events),
        'total_events_all': total_events_all,
        'q': q,
        'selected_filter': selected_filter,
        'sort': sort,
        'pagination_query': pagination_query,
    })


@staff_required
def analytics(request):
    total_antraege = Antrag.objects.count()
    accepted = Antrag.objects.filter(status=Antrag.STATUS_ACCEPTED).count()
    declined = Antrag.objects.filter(status=Antrag.STATUS_DECLINED).count()
    in_progress = Antrag.objects.filter(status=Antrag.STATUS_IN_PROGRESS).count()
    total_responded = accepted + declined
    acceptance_rate = round(accepted / total_responded * 100) if total_responded else 0

    by_klasse = list(
        Antrag.objects.values('klasse').annotate(count=Count('id')).order_by('-count')
    )
    max_klasse = max((x['count'] for x in by_klasse), default=1)

    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly = list(
        Antrag.objects.filter(erstellt_am__gte=twelve_months_ago)
        .annotate(month=TruncMonth('erstellt_am'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    max_monthly = max((x['count'] for x in monthly), default=1)

    teacher_stats = list(
        Anfrage.objects.exclude(response=Anfrage.NOT_RESPONDED)
        .values('email')
        .annotate(
            total=Count('id'),
            accepted=Count(Case(When(response=Anfrage.ACCEPTED, then=1), output_field=IntegerField())),
            declined=Count(Case(When(response=Anfrage.DECLINED, then=1), output_field=IntegerField())),
        )
        .order_by('-total')[:10]
    )
    for t in teacher_stats:
        local = t['email'].split('@')[0]
        t['name'] = ' '.join(w.capitalize() for w in local.split('.'))
        t['rate'] = round(t['accepted'] / t['total'] * 100) if t['total'] else 0
    max_teacher = max((t['total'] for t in teacher_stats), default=1)

    top_students = list(
        Antrag.objects.values('user__first_name', 'user__last_name', 'user__email')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    max_student = max((s['count'] for s in top_students), default=1)

    responded_anfragen = list(
        Anfrage.objects.filter(responded_at__isnull=False).values('created', 'responded_at')
    )
    avg_days = None
    if responded_anfragen:
        total_sec = sum((r['responded_at'] - r['created']).total_seconds() for r in responded_anfragen)
        avg_days = round(total_sec / len(responded_anfragen) / 86400, 1)

    return render(request, 'adminview/analytics.html', {
        'total_antraege': total_antraege,
        'accepted': accepted,
        'declined': declined,
        'in_progress': in_progress,
        'total_responded': total_responded,
        'acceptance_rate': acceptance_rate,
        'by_klasse': by_klasse,
        'max_klasse': max_klasse,
        'monthly': monthly,
        'max_monthly': max_monthly,
        'teacher_stats': teacher_stats,
        'max_teacher': max_teacher,
        'top_students': top_students,
        'max_student': max_student,
        'avg_days': avg_days,
    })


@staff_required
def antraege_list(request):
    qs = Antrag.objects.select_related('user').order_by('-erstellt_am')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    klasse = request.GET.get('klasse', '')
    sort = request.GET.get('sort', '-erstellt_am')

    if q:
        qs = qs.filter(
            Q(titel__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q)
        )
    if status in (Antrag.STATUS_IN_PROGRESS, Antrag.STATUS_ACCEPTED, Antrag.STATUS_DECLINED):
        qs = qs.filter(status=status)
    if klasse:
        qs = qs.filter(klasse=klasse)

    allowed_sorts = {
        'erstellt_am': 'erstellt_am', '-erstellt_am': '-erstellt_am',
        'anfangsdatum': 'anfangsdatum', '-anfangsdatum': '-anfangsdatum',
        'user': 'user__last_name', 'status': 'status',
    }
    qs = qs.order_by(allowed_sorts.get(sort, '-erstellt_am'))

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    klasse_choices = Antrag.KLASSE_CHOICES

    return render(request, 'adminview/antraege_list.html', {
        'page_obj': page_obj,
        'q': q, 'status': status, 'klasse': klasse, 'sort': sort,
        'klasse_choices': klasse_choices,
        'total': qs.count(),
    })


def _register_pdf_fonts():
    """
    Register DejaVu Sans (Unicode-capable) with ReportLab if the font files
    are present (installed via fonts-dejavu-core in the container).  Falls
    back silently to the built-in Helvetica when the font is unavailable
    (e.g. local development without the package installed).
    Returns the font-family name to embed in the PDF CSS.
    """
    import os
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        base = '/usr/share/fonts/truetype/dejavu/'
        regular = os.path.join(base, 'DejaVuSans.ttf')
        bold    = os.path.join(base, 'DejaVuSans-Bold.ttf')
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont('DejaVuSans', regular))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold))
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans-Bold')
            return 'DejaVuSans'
    except Exception:
        pass
    return 'Helvetica'


@staff_required
def antrag_pdf(request, antrag_id):
    try:
        from xhtml2pdf import pisa
    except (ModuleNotFoundError, ImportError):
        return HttpResponse(
            'PDF-Export ist aktuell nicht verfügbar (fehlendes Paket: xhtml2pdf).',
            status=503,
        )
    import io

    antrag = get_object_or_404(Antrag.objects.select_related('user').prefetch_related('anfrage_set'), id=antrag_id)
    anfragen = antrag.anfrage_set.all().order_by('created')

    pdf_font = _register_pdf_fonts()

    html = render_to_string('adminview/antrag_pdf_template.html', {
        'antrag': antrag,
        'anfragen': anfragen,
        'generated': timezone.now(),
        'pdf_font': pdf_font,
    })

    buf = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buf, encoding='utf-8')
    if pisa_status.err:
        return HttpResponse('Fehler beim Erstellen der PDF-Datei.', status=500)

    buf.seek(0)
    lastname = antrag.user.last_name or antrag.user.email.split('@')[0]
    filename = f"Freistellungsantrag_{antrag.id}_{lastname}.pdf"
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
