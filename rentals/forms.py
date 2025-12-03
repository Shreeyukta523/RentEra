
from django.contrib.auth.password_validation import validate_password
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, ListOfCitizenship
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import requests
import re
from django.contrib.auth.forms import AuthenticationForm


def verify_email_with_hunter(email):
    api_key = '332a23750c6181cbe4fa87228b4585cfcb2f33ed'  # Replace with your Hunter.io API key
    url = 'https://api.hunter.io/v2/email-verifier'
    
    params = {
        'email': email,
        'api_key': api_key,
    }
    
    try:
        response = requests.get(url, params=params)#make an HTTP GET request to a URL, with parameters included in the query string.
        response.raise_for_status()  # Raise exception for HTTP errors

        data = response.json()
        print(f"API Response for {email}: {data}")  # Debugging: Print the full response

        result = data.get('data', {}).get('result')
        if result == 'deliverable' or result == 'risky':
            return True  # Accept deliverable and risky emails
        else:
            return False  # Invalid email
    except requests.exceptions.RequestException as e:
        print(f"Error verifying email: {e}")
        return False

class RegisterForm(UserCreationForm):
    # Override the password fields to be standard CharFields
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True)
    address = forms.CharField(max_length=50, required=True)
    phone_number = forms.CharField(max_length=10)
    citizenship_number = forms.CharField(max_length=14)

    class Meta:
        model = User
        # Remove password1 and password2 from the fields list,
        # as we are handling them manually now.
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 7:
            raise forms.ValidationError("Username must be at least 7 characters long.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("This field is required.")
        
        # Verify the email using Hunter.io API
        if not verify_email_with_hunter(email):
            raise forms.ValidationError("The email address is invalid.")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already taken.")
        return email
    
    def clean_citizenship_number(self):
        citizenship_number = self.cleaned_data.get('citizenship_number')
        citizenship_pattern = r'^\d{2}-\d{2}-\d{2}-\d{5}$'

        if len(citizenship_number) != 14:
            raise forms.ValidationError("Citizenship number must be exactly 14 characters long.")
        
        elif not re.fullmatch(citizenship_pattern, citizenship_number):
            raise forms.ValidationError("Citizenship number must be in the format XX-XX-XX-XXXXX (numbers only).")

        return citizenship_number
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if len(phone_number) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits long.")

        if not re.fullmatch(r'^\d{10}$', phone_number):
            raise forms.ValidationError("Phone number can only contain digits (0-9).")

        return phone_number
    
    def clean(self):
        cleaned_data = super().clean()

        password = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        # --- Password Mismatch and Strength Validation ---
        if password and password2:
            if password != password2:
                self.add_error('password2', "Passwords don't match.")
            else:
                try:
                    validate_password(password, user=None)
                except ValidationError:
                    self.add_error('password1', "This password is too short. It must contain at least 8 characters.")
        # --- Citizenship Mismatch Validation ---
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        citizenship_number = cleaned_data.get('citizenship_number')

        if first_name and last_name and citizenship_number:
            matching_record = ListOfCitizenship.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                citizenship_number=citizenship_number
            ).exists()

            if not matching_record:
                self.add_error(
                    'citizenship_number',
                    "Mismatch: Please check your name and citizenship number. Add the valid details."
                )
        
        return cleaned_data
    
class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages['invalid_login'] = "Invalid username or password."

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_image']


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username',)

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone_number', 'address')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')

        if not phone_number:
            return phone_number

        if len(phone_number) != 10:
            raise forms.ValidationError('Phone number must be exactly 10 digits.')

        if not phone_number.isdigit():
            raise forms.ValidationError('Phone number must contain only digits.')

        return phone_number
    
    

class ProfileEditForm(forms.ModelForm):
    # This field is for updating the username on the User model
    username = forms.CharField(max_length=150)

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['username'].initial = self.user.username

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        
        # Check if the phone number is provided and has more than 10 digits
        if phone_number and len(phone_number) > 10:
            raise forms.ValidationError("Phone number cannot be more than 10 digits.")
        
        # You might also want to ensure it contains only digits
        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
            
        return phone_number

    def save(self, commit=True):
        if self.user:
            self.user.username = self.cleaned_data['username']
            self.user.save()
        return super().save(commit=commit)



