from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserEditForm
from users.forms import Sign_Up_Form
from users.models import CustomUser
from users.views import signup


User = get_user_model()

@login_required
def adminview(request, user_id=None):
    users = User.objects.all().order_by('email')
    
    if user_id:
        edit_user = get_object_or_404(User, id=user_id)
        if request.method == 'POST':
            form = UserEditForm(request.POST, instance=edit_user)
            if form.is_valid():
                form.save()
                messages.success(request, f"User {edit_user.email} updated successfully")
                return redirect('adminview-home')
        else:
            form = UserEditForm(instance=edit_user)
    else:
        edit_user = None
        form = Sign_Up_Form()

    if request.method == 'POST' and 'delete_user' in request.POST:
        user_id_to_delete = request.POST.get('delete_user')
        user_to_delete = get_object_or_404(User, id=user_id_to_delete)
        user_to_delete.delete()
        messages.success(request, f'User {user_to_delete.email} deleted successfully')
        return redirect('adminview-home')
    
    context = {
        'users': users,
        'edit_user': edit_user,
        'form': form
    }
    
    return render(request, 'adminview/home.html', context)

def adding(request):
    if request.method == 'POST':
        form = Sign_Up_Form(request.POST)
        if form.is_valid():
            form.save()

            return redirect('adminview-home') 
    else:
        form = Sign_Up_Form()
    
    return render(request, 'adminview/add_user.html', {'form': form})

@login_required
<<<<<<< HEAD
def admin_dashboard(request):
    if not is_app_admin(request.user):
        return redirect ('login')
    
    return render(request, 'adminview.html')

def adminview(request):
    return render(request, 'adminview.html')
>>>>>>> 57f056b (adminview_first)
=======
def csv(request):
    return render(request, 'adminview/csv.html')
>>>>>>> ffdd6c1 (adminview user-list added, editing possible)
