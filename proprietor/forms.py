from django import forms
from django.contrib.auth.models import User
from .models import Property, Facility, PropertyMedia
from rentals.models import UserProfile
from django.contrib.auth.forms import UserCreationForm # This import might not be needed for PropertyForm
from .widgets import LeafletSearchMapWidget

class PropertyForm(forms.ModelForm):
    facilities = forms.ModelMultipleChoiceField(
        queryset=Facility.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Property
        # When you define model = Property in your Meta class and specify fields,
        # Django automatically inspects your Property model. For each field listed,
        # it intelligently creates the corresponding Django form field (CharField for a models.CharField,
        # IntegerField for a models.IntegerField, ModelMultipleChoiceField for a models.ManyToManyField, etc.).
        # When you define a field in your Property model (e.g., name = models.CharField(max_length=200)),
        # you're setting database-level constraints and validation rules.
        # ModelForm automatically inherits and applies these rules to the form fields.
        # You don't have to manually declare each form field with its type, max_length, required status, etc.,
        # if those properties are already defined in your model.
        # This dramatically reduces the amount of code you write and maintain.
        # If name is required=True (the default for CharField), the form field will also be required.
        # max_length will be respected.
        fields = [
            'name', 'province', 'address', 'District', 'ward_no',
            'price', 'property_type', 'number_of_rooms','Municipality',
            'description', 'facilities','sheet_no','land_no',
            'latitude',   # Ensure these are here
            'longitude'   # Ensure these are here
        ]
        input_attrs = {'class': 'form-control'}
        widgets = {
                    # Text/Number Inputs (use TextInput, NumberInput, or default will work if no custom attrs needed)
                    'name': forms.TextInput(attrs=input_attrs),
                    'address': forms.TextInput(attrs=input_attrs),
                    'Municipality': forms.TextInput(attrs=input_attrs),
                    'ward_no': forms.NumberInput(attrs=input_attrs),
                    'sheet_no': forms.TextInput(attrs=input_attrs),
                    'land_no': forms.TextInput(attrs=input_attrs),
                    'number_of_rooms': forms.NumberInput(attrs=input_attrs),
                    'price': forms.NumberInput(attrs=input_attrs),
                    'District': forms.TextInput(attrs=input_attrs),
                    # Select Inputs (already had them, but ensuring consistency)
                    'province': forms.Select(attrs=input_attrs),
                    'property_type': forms.Select(attrs=input_attrs),

                    # Textarea
                    'description': forms.Textarea(attrs=input_attrs),
                    
                    # Map/Hidden Inputs (do not apply 'form-control' here)
                    'latitude': LeafletSearchMapWidget(), 
                    'longitude': forms.HiddenInput()
                }

        # widgets = {...}: This dictionary allows you to specify a custom HTML widget for specific form fields.

        # 'province': forms.Select(...) and 'property_type': forms.Select(...) tell Django to use a <select> HTML element for these fields, typically for dropdowns.

        # 'latitude': LeafletSearchMapWidget() and 'longitude': forms.HiddenInput() are particularly interesting.

        # LeafletSearchMapWidget(): This indicates you're using a custom widget (likely from a third-party library like django-map-widgets or django-leaflet) that renders an interactive Leaflet map, allowing users to select a location and, presumably, populate the latitude and longitude fields.

        # forms.HiddenInput(): This means the longitude field will be a hidden HTML input, suggesting its value is set programmatically (e.g., by the LeafletSearchMapWidget) rather than by direct user input.


        # In Django forms, a widget is simply a class that defines how a form field is rendered as an HTML input element (or other HTML structure) in your template.
        # province and property_type: By default, models.CharField (even with choices) would render as a text input. By specifying forms.Select, you explicitly tell Django to render these as HTML <select> (dropdown) elements. You also added a class attribute for styling.

        # latitude: This field would default to forms.NumberInput (for FloatField). But you want a map! So you assign your custom LeafletSearchMapWidget to it. This widget is responsible for rendering the map HTML and associated JavaScript.

        # longitude: This would also default to forms.NumberInput. But since its value is likely set by the map widget, you don't want the user to see or manually input it. So you assign forms.HiddenInput to render it as <input type="hidden">.

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        # These fields are available for the template to render inputs
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address', 'profile_image']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }