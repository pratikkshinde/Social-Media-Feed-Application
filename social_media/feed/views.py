from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, ProfileForm
from .models import Profile

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect('feed:home')
    else:
        form = RegisterForm()
    return render(request, 'feed/register.html', {'form': form})

@login_required
def home(request):
    return render(request, 'feed/home.html')

@login_required
def profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('feed:profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'feed/profile.html', {'form': form})
