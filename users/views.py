from django.shortcuts import render, redirect
from .forms import Sign_Up_Form

def login(request):
    return render(request, "users/login.html")

def signup(request):
    if request.method == 'POST':
        form = Sign_Up_Form(request.POST)
        if form.is_valid():
            form.save()
            # Optionally, you can log the user in here after signup.
            return redirect('login')  # Replace 'login' with your login URL name.
    else:
        form = Sign_Up_Form()
    
    return render(request, 'users/signup.html', {'form': form})
def login_success(request):
    if request.user.is_authenticated:
        if request.user.is_app_admin:
            return redirect ('adminview')
        else:
            return redirect('')
        return redirect('login')