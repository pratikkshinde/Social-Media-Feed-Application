from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Post

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_pic']

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['image', 'caption']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'visually-hidden upload-input',
                'accept': 'image/*',
                'aria-describedby': 'uploadHelp',
            }),
            'caption': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Write a caption for this moment...',
                'class': 'form-control caption-input',
            }),
        }