from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from .forms import UserEditForm, add_lehrer_Form
from users.forms import Sign_Up_Form
from users.models import CustomUser
from users.views import signup
from django.db.models import Q
from django.http import JsonResponse
from antraege.models import Lehrer
from django.urls import reverse


User = get_user_model()

def validate_afra_email(email):
    if not email.endswith('@afra.lernsax.de'):
        raise ValidationError('Nur E-Mail-Adressen, die mit "@afra.lernsax.de" enden, sind zulässig.')
    return email

@login_required
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
                'name':f"{user.first_name} {user.last_name}",
                #'birth_date': user.birth_date.strftime('%Y-%m-%d') if user.birth_date else '',
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
            emails = [user.email for user in users]
            users.delete()
            messages.success(request, f'{len(selected_users)} Benutzer wurden gelöscht')
        return redirect('adminview-home')
    
    context = {
        'users': users,
        'edit_user': edit_user,
        'search_query': search_query,
        'button_url': reverse('adminview-csv'),
    }
    
    return render(request, 'adminview/home.html', context)

@login_required
def adding(request):
    if request.method == 'POST':
        form = Sign_Up_Form(request.POST)
        if form.is_valid():
            # Validate email format before saving
            try:
                validate_afra_email(form.cleaned_data['email'])
                form.save()
                return redirect('adminview-home')
            except ValidationError as e:
                form.add_error('email', e)
    else:
        form = Sign_Up_Form()
    
    return render(request, 'adminview/add_user.html', {'form': form})

@login_required
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

@login_required
def csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            # Check if file is CSV
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('adminview-csv')
                
            # Process CSV file
            try:
                csv_data = csv_file.read().decode('utf-8')
                import io
                import csv
                from datetime import datetime
                
                io_string = io.StringIO(csv_data)
                reader = csv.reader(io_string, delimiter=';')
                
                success_count = 0
                error_count = 0
                errors = []
                
                for row in reader:
                    try:
                        if len(row) >= 3:
                            email = row[1].strip()
                            name_parts = row[2].strip().split (' ', 1)
                            first_name = name_parts[0]
                            last_name = name_parts[1] if len(name_parts) > 1 else ''
                            
                            # Validate email format
                            try:
                                validate_afra_email(email)
                            except ValidationError as e:
                                errors.append(f"Invalid email for row {email}: {str(e)}")
                                error_count += 1
                                continue

                            #birth_date = None
                            #if birth_date_str:
                                #date_formats = [
                                    #'%Y-%m-%d',  # YYYY-MM-DD
                                    #'%d.%m.%Y',  # DD.MM.YYYY
                                    #'%d.%m.%y',  # DD.MM.YY (Excel default)
                                    #'%m/%d/%Y',  # MM/DD/YYYY
                                    #'%m/%d/%y',  # MM/DD/YY
                                #]
                                
                                #for date_format in date_formats:
                                    #try:
                                        #birth_date = datetime.strptime(birth_date_str, date_format).date()
                                        #break  # Exit the loop if successful
                                    #except ValueError:
                                        #continue
                                
                                #if birth_date is None:
                                    #errors.append(f"Invalid date format for {email}: {birth_date_str}")
                                    #error_count += 1
                                    #continue
                            
                            # Check if user already exists
                            if not CustomUser.objects.filter(email=email).exists():
                                user = CustomUser(
                                    email=email,
                                    first_name=first_name,
                                    last_name=last_name,
                                )
                                user.save()
                                success_count += 1
                            else:
                                errors.append(f"User with email {email} already exists")
                                error_count += 1
                        else:
                            errors.append(f"Row has insufficient data: {row}")
                            error_count += 1
                    except Exception as e:
                        errors.append(f"Error processing row: {row}. Error: {str(e)}")
                        error_count += 1
                
                # Show results
                if success_count > 0:
                    messages.success(request, f'Successfully created {success_count} user(s)')
                if error_count > 0:
                    messages.warning(request, f'Failed to create {error_count} user(s)')
                    for error in errors[:10]:  # Show only first 10 errors
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... and {len(errors) - 10} more errors")
                        
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
            
            return redirect('adminview-home')
    
    return render(request, 'adminview/csv.html')

@login_required
def lehrer(request, lehrer_id=None):
    search_query = request.GET.get('q', '')
    if search_query:
        lehrers = Lehrer.objects.filter(
            Q(email__icontains=search_query) | 
            Q(name__icontains=search_query)
        ).order_by('email')
    else:
        lehrers = Lehrer.objects.all().order_by('email')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        lehrer_data = []
        for lehrer in lehrers:
            lehrer_data.append({
                'id': lehrer.id,
                'email': lehrer.email,
                'name':f"{lehrer.name}",
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
        
        lehrer = Lehrer.objects.filter(id__in=selected_lehrers)

        if action == 'delete':
            emails = [lehrer.email for lehrer in lehrers]
            lehrer.delete()
            messages.success(request, f'{len(selected_lehrers)} Lehrer wurden gelöscht')
        return redirect('lehrer')
    
    context = {
        'lehrers': lehrers,
        'edit_lehrer': edit_lehrer,
        'search_query': search_query,
        'button_url': reverse('lehrer_csv'),
    }
    
    return render(request, 'adminview/lehrer.html', context)

@login_required
def add_lehrer(request):
    form=add_lehrer_Form(request.POST)
    if request.method == 'POST':
        form = add_lehrer_Form(request.POST)
        if form.is_valid():
            try:
                validate_afra_email(form.cleaned_data['email'])
                form.save()
                return redirect('lehrer')
            except ValidationError as e:
                form.add_error('email', e)
    else:
        form = add_lehrer_Form()
    
    return render(request, 'adminview/add_lehrer.html', {'form': add_lehrer_Form})

@login_required
def edit_lehrer(request, lehrer_id=None):
    if lehrer_id:
        edit_lehrer = get_object_or_404(Lehrer, id=lehrer_id)
        if request.method == 'POST':
            form = add_lehrer_Form(request.POST, instance=edit_lehrer)
            if form.is_valid():
                try:
                    validate_afra_email(form.cleaned_data['email'])
                    form.save()
                    messages.success(request, f"Lehrer {edit_lehrer.email} erfolgreich aktualisiert")
                    return redirect('lehrer')
                except ValidationError as e:
                    form.add_error('email', e)
        else:
            form = add_lehrer_Form(instance=edit_lehrer)
    else:
        edit_lehrer = None
        form = add_lehrer_Form()
    return render(request, 'adminview/edit_lehrer.html', {'form': form, 'edit_lehrer': edit_lehrer})

@login_required
def lehrer_csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            # Check if file is CSV
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('lehrer_csv')
                
            # Process CSV file
            try:
                csv_data = csv_file.read().decode('utf-8')
                import io
                import csv
                from datetime import datetime
                
                io_string = io.StringIO(csv_data)
                reader = csv.reader(io_string, delimiter=';')

                success_count = 0
                error_count = 0
                errors = []
                
                for row in reader:
                    try:
                        if len(row) >= 3:
                            email = row[1].strip()
                            name = row[2].strip()
                            
                            try:
                                validate_afra_email(email)
                            except ValidationError as e:
                                errors.append(f"Invalid email for row {email}: {str(e)}")
                                error_count += 1
                                continue

                            #birth_date = None
                            #if birth_date_str:
                                #date_formats = [
                                    #'%Y-%m-%d',  # YYYY-MM-DD
                                    #'%d.%m.%Y',  # DD.MM.YYYY
                                    #'%d.%m.%y',  # DD.MM.YY (Excel default)
                                    #'%m/%d/%Y',  # MM/DD/YYYY
                                    #'%m/%d/%y',  # MM/DD/YY
                                #]
                                
                                #for date_format in date_formats:
                                    #try:
                                        #birth_date = datetime.strptime(birth_date_str, date_format).date()
                                        #break  # Exit the loop if successful
                                    #except ValueError:
                                        #continue
                                
                                #if birth_date is None:
                                    #errors.append(f"Invalid date format for {email}: {birth_date_str}")
                                    #error_count += 1
                                    #continue
                            
                            # Check if user already exists
                            if not Lehrer.objects.filter(email=email).exists():
                                lehrer = Lehrer(
                                    email=email,
                                    name=name
                                )
                                lehrer.save()
                                success_count += 1
                            else:
                                errors.append(f"Es existiert bereits ein Lehrer mit der Email {email}")
                                error_count += 1
                        else:
                            errors.append(f"Zeile hat ungültige Daten: {row}")
                            error_count += 1
                    except Exception as e:
                        errors.append(f"Error processing row: {row}. Error: {str(e)}")
                        error_count += 1
                
                # Show results
                if success_count > 0:
                    messages.success(request, f'Erfolgreich {success_count} Lehrer erstellt')
                if error_count > 0:
                    messages.warning(request, f'{error_count} Lehrer konnten nicht erstellt werden')
                    for error in errors[:10]:  # Show only first 10 errors
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... and {len(errors) - 10} more errors")
                        
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
            
            return redirect('lehrer')
    
    return render(request, 'adminview/lehrer_csv.html')
