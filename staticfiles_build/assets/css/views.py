from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import RegisterForm, ProfileImageForm
from django.http import HttpResponseRedirect, JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
import base64
from django.contrib.auth.tokens import default_token_generator

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.mail import EmailMessage
import logging
from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.forms import AuthenticationForm
from .forms import LoginForm

from .middlewares import auth, guest
from .decorators import renter,proprietor


from .models import UserProfile, Request
from proprietor.models import Property

from .models import UserProfile, Request, Message
from proprietor.models import Property, Facility

import requests

from django.db.models import Q, F

from .forms import UserForm, UserProfileForm, ProfileEditForm # Import all forms


from django.urls import reverse

from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages as django_messages
from django.templatetags.static import static 

from django.db import models


from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages as django_messages
from django.templatetags.static import static 

from django.db import models
import time

def home(request):
    return render(request, 'index.html')

def send_activation_email(user, request,role):
    token=default_token_generator.make_token(user)      #consists of time limited data so can expire in some time
    uid = urlsafe_base64_encode(force_bytes(user.pk))           #takes user's pk then converts into string then encodes it to byte in base64 fromat which is later received in activate_account functions if link is clicked


    current_site=get_current_site(request)           #get current site domain eg: ;pcahpst:8000
    activation_link=f"http://{current_site}/activate/{uid}/{token}/{role}"       #creates full URL eg:http://localhost:8000/rentals/activate/NjM/tokenstringhere/

    email_subject = 'Activate your Rentera account'
    email_body = render_to_string('activation_email.html', {
        'user': user,
        'activation_link': activation_link
    })

    #send email
    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email='krishalasth34@gmail.com',
        to=[user.email],
    )
    email.content_subtype = "html"  #to ensure html page is rendered
    email.send()
    
# this function is triggered when the user clicks on activation link sent in email
def activate_account(request, uidb64, token, role):
    try:
        #when user clicks on activation link, uidb64 is decoded to get the user id
        uid=urlsafe_base64_decode(uidb64)       # User ID is originally an integer (pk), which was encoded to base64 for the URL
        user=User.objects.get(pk=uid)           # uid is currently bytes (e.g., b'1'); Django auto-converts it, but you can also do uid = int(uid.decode())

        logging.debug(f'Activating user {user.username}, token valid:{default_token_generator.check_token(user,token)}')

        if default_token_generator.check_token(user,token):
            role = role
            user.is_active=True
            user.save()

            profile = UserProfile.objects.get(user=user)
            profile.is_verified = True
            profile.save()


            messages.success(request, "Your account has been activated. You can now log in.")
            return redirect('login')
        
        else:
            messages.error(request,"Activation link is invalid or has expired.")
            return redirect('login')
        
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:

        logging.error(f'Error during activation: {e}')
        messages.error(request,"Invalid activation link")
        return redirect('login')

#activation link consists  of userid(encoded in base64 format) and a token to verify link is valid
#when user clicks the link, user Id is decoded and token is checked for validity and if yes, account is activated and a user profile is created

@guest
def signup(request):
    if request.method =='POST':
        form=RegisterForm(request.POST)#classinforms.py


       
        
        if form.is_valid():#
        #Here's the short version of how clean_FIELDNAME methods work in Django forms:

# When a form is submitted and you call form.is_valid():

# Django automatically calls clean_FIELDNAME() for each field you've defined this method for (e.g., clean_username, clean_email).

# These methods validate individual fields after basic checks.

# If a clean_FIELDNAME() method finds an issue, it raises forms.ValidationError, and the form becomes invalid.

# If all clean_FIELDNAME() methods pass, Django then calls the form's overall clean() method (if you have one) for multi-field validation.

# If everything passes, form.is_valid() returns True, and form.cleaned_data contains the valid input.
        #The error messages are sent back to the template, but they are attached to the form object itself, not as a separate message. When form.is_valid() returns False, the form.errors attribute is populated.
            user=form.save(commit = False)
            user.is_active= False       #for deactivating email until confirmation
            user.save()
            address = form.cleaned_data['address']
            phone = form.cleaned_data['phone_number']
            c = form.cleaned_data['citizenship_number']
            role = form.cleaned_data['role']
            print(address,phone,role,user)

            userprofile = UserProfile.objects.create(
            user=user,
            phone_number=phone,
            role=role,
            address=address,
            citizenship_number=c,
            is_verified=False )
            userprofile.save()


            #send email activation link
            send_activation_email(user, request, role)
        
            messages.success(request, "Registration successful. Please check your email to activate your account.")
            return redirect('login')
        else:
            messages.error(request,"Form submission failed.")#msglinkedtotherequest
            
    else:
        initial_data={ 
            'username' :'', 
            'email':'',
            'password1':'', 
            'password2':'', 
            'first_name':'', 
            'last_name':'', 
            'role':''
            }
        form=RegisterForm(initial=initial_data)

    return render(request, 'signup.html', {'form' : form})
#     The same form instance you pass to the template has the error messages stored inside it.

# Each field's errors are accessible by form.fieldname.errors.

# views.py

@guest 
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST) 
        if form.is_valid():
            user = form.get_user()
            if user.is_active:
                login(request, user)
                return redirect(request.POST.get('next', 'home'))
            else:
                form.add_error(None, "Your account is not activated. Please check your email.")
    else:
        initial_data={'username':'', 'password' : ''}
        form = LoginForm(initial=initial_data)

    if 'next' in request.GET:
        # Note: messages.info is generally fine to keep here as it's not a form-specific error.
        messages.info(request, "Please login to access this page.")

    return render(request, 'login.html', {'form': form})
@auth
def logout_confirm(request):
    #logs out the user
    logout(request)
    return redirect('login')                  #for logout to work
 
from django.db.models import Q

def property_view(request):
    properties_list = Property.objects.all().order_by('-created_at')

    search = request.GET.get('search', '').strip()
    filters = {
        'province': request.GET.get('province', ''),
        'district': request.GET.get('district', '').strip(),
        'property_type': request.GET.get('property_type', ''),
        'max_price': request.GET.get('max_price', ''),
        'facilities': request.GET.getlist('facilities'),
    }

    selected_filters = {
        'search': search,
        **filters,
    }

    if search:
        # Search on name OR address
        properties_list = properties_list.filter(
            Q(name__icontains=search) | Q(address__icontains=search)
        )
        # Clear filters so they don't conflict in template
        selected_filters.update({k: '' if k != 'search' else search for k in filters.keys()})
    else:
        # Apply filters only if no search
        if filters['province']:
            properties_list = properties_list.filter(province=filters['province'])
        if filters['district']:
            properties_list = properties_list.filter(District__icontains=filters['district'])
        if filters['property_type']:
            properties_list = properties_list.filter(property_type=filters['property_type'])
        if filters['max_price']:
            try:
                max_price = float(filters['max_price'])
                properties_list = properties_list.filter(price__lte=max_price)
            except ValueError:
                pass
        for facility_id in filters['facilities']:
            properties_list = properties_list.filter(facilities__id=facility_id)
        properties_list = properties_list.distinct()

    paginator = Paginator(properties_list, 6)
    page_number = request.GET.get('page')
    properties = paginator.get_page(page_number)

    property_types = Property.objects.values_list('property_type', flat=True).distinct()
    facilities = Facility.objects.all()

    PROVINCES = [
        ('1', 'Province No. 1 (Koshi)'),
        ('2', 'Province No. 2 (Madhesh)'),
        ('3', 'Province No. 3 (Bagmati)'),
        ('4', 'Province No. 4 (Gandaki)'),
        ('5', 'Province No. 5 (Lumbini)'),
        ('6', 'Province No. 6 (Karnali)'),
        ('7', 'Province No. 7 (Sudurpashchim)'),
    ]

    context = {
        'properties': properties,
        'property_types': property_types,
        'facilities': facilities,
        'PROVINCES': PROVINCES,
        'selected_filters': selected_filters,
    }

    return render(request, 'properties.html', context)

def contact(request):
    return render(request, 'contact.html')

@login_required(login_url='login')
def update_profile_img(request):
    profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # Check the user's role for redirection
            if request.user.userprofile.role == 'proprietor':
                return redirect('proprietordashboard')
            else:
                return redirect('myprofile')
    else:
        form = ProfileImageForm(instance=profile)

    return render(request, 'update_profimg.html', {'form': form})

def propertydetails(request, slug):
    property_obj = get_object_or_404(Property, slug=slug)
    user_profile = request.user.userprofile
    is_proprietor = (user_profile.role == 'proprietor')

    # Initialize all to None
    renter_has_pending_request = False
    renter_has_accepted_request = False
    renter_has_rejected_request = False
    renter_has_cancelled_request = False

    current_pending_request = None # Store the actual request object if pending
    current_accepted_request = None # Store the actual request object if accepted
    current_rejected_request = None
    current_cancelled_request = None

    if user_profile.role == 'renter':
        # Fetch the most recent request of each relevant status
        # Using .first() is good if you only care about the existence or the latest one
        # For 'pending', we really only care if one exists.
        current_pending_request = Request.objects.filter(
            renter=user_profile,
            property=property_obj,
            status='pending'
        ).order_by('-created_at').first() # Get the most recent if multiple exist (though ideally only one)

        if current_pending_request:
            renter_has_pending_request = True

        current_accepted_request = Request.objects.filter(
            renter=user_profile,
            property=property_obj,
            status='accepted'
        ).order_by('-created_at').first()
        if current_accepted_request:
            renter_has_accepted_request = True

        current_rejected_request = Request.objects.filter(
            renter=user_profile,
            property=property_obj,
            status='rejected'
        ).order_by('-created_at').first()
        if current_rejected_request:
            renter_has_rejected_request = True

        current_cancelled_request = Request.objects.filter(
            renter=user_profile,
            property=property_obj,
            status='cancelled'
        ).order_by('-created_at').first()
        if current_cancelled_request:
            renter_has_cancelled_request = True

    context = {
        'property': property_obj,
        'is_proprietor': is_proprietor,
        'renter_has_pending_request': renter_has_pending_request,
        'current_pending_request': current_pending_request, # Pass the object for its ID if needed for cancellation
        'renter_has_accepted_request': renter_has_accepted_request,
        'current_accepted_request': current_accepted_request,
        'renter_has_rejected_request': renter_has_rejected_request,
        'current_rejected_request': current_rejected_request,
        'renter_has_cancelled_request': renter_has_cancelled_request,
        'current_cancelled_request': current_cancelled_request,
    }
    return render(request, 'property_details.html', context)

@renter
def profile_page(request):
    user = request.user
    user_profile = user.userprofile
    current_timestamp = int(time.time())

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        user_profile_form = UserProfileForm(request.POST, instance=user_profile)

        if user_form.is_valid() and user_profile_form.is_valid():
            user_form.save()
            user_profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('myprofile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # This is the crucial part that pre-populates the forms
        user_form = UserForm(instance=user)
        user_profile_form = UserProfileForm(instance=user_profile)

    context = {
        'user_form': user_form,
        'user_profile_form': user_profile_form,
        'current_timestamp': current_timestamp,
    }
    return render(request, 'profile.html', context)

# --- MODIFIED: send_property_request to enforce single pending request ---
@login_required
def send_property_request(request, slug):
    if request.method == 'POST':
        property_obj = get_object_or_404(Property, slug=slug)
        renter_profile = request.user.userprofile

        if renter_profile.role != 'renter':
            messages.error(request, "Only renters can send property requests.")
            return redirect('propertydetails', slug=slug)

        if property_obj.user_profile == renter_profile:
            messages.warning(request, "You cannot send a request for your own property.")
            return redirect('propertydetails', slug=slug)

        # --- KEY LOGIC HERE ---
        # Check if there is ANY active (pending or accepted) request from this renter for this property.
        # This prevents sending a new request if one is already in progress or accepted.
        active_request_exists = Request.objects.filter(
            renter=renter_profile,
            property=property_obj
        ).filter(
            Q(status='pending') | Q(status='accepted') # Look for either pending OR accepted
        ).exists()

        if active_request_exists:
            messages.info(request, "You already have an active (pending or accepted) request for this property.")
            return redirect('propertydetails', slug=slug)

        # If we reach here, no active request exists, so a new one can be created
        proprietor_profile = property_obj.user_profile
        Request.objects.create(
            renter=renter_profile,
            proprietor=proprietor_profile,
            property=property_obj,
            status='pending'
        )
        messages.success(request, f"Your request for '{property_obj.name}' has been sent to {proprietor_profile.user.username}.")
        return redirect('propertydetails', slug=slug)
    else:
        return redirect('propertydetails', slug=slug)

# --- cancel_property_request (unchanged - operates on a specific request ID) ---
@login_required
def cancel_property_request(request, request_id):
    req = get_object_or_404(Request, id=request_id)
    user_profile = request.user.userprofile

    if req.renter == user_profile and req.status == 'pending':
        req.status = 'cancelled'
        req.save()
        messages.info(request, f"Your request for '{req.property.name}' has been cancelled.")
    else:
        messages.error(request, "You are not authorized to cancel this request or it cannot be cancelled at this stage.")

    return redirect(f"{reverse('myprofile')}?section=notifications")

# --- notifications (unchanged - just lists requests) ---
@login_required
def notifications(request):
    user_profile = request.user.userprofile

    if user_profile.role == 'renter':
        sent_requests = Request.objects.filter(renter=user_profile).order_by('-created_at')
        context = {
            'user_role': 'renter',
            'sent_requests': sent_requests,
        }
    elif user_profile.role == 'proprietor':
        received_requests = Request.objects.filter(proprietor=user_profile).order_by('-created_at')
        context = {
            'user_role': 'proprietor',
            'received_requests': received_requests,
        }
    else:
        messages.warning(request, "You do not have any specific notifications to display.")
        return redirect('home')

    return render(request, 'notifications.html', context)

# --- manage_request (unchanged - operates on a specific request ID) ---
@login_required
def manage_request(request, request_id, action):
    req = get_object_or_404(Request, id=request_id)
    user_profile = request.user.userprofile

    if req.proprietor != user_profile:
        messages.error(request, "You are not authorized to manage this request.")
        return redirect('notifications')

    if request.method == 'POST':
        if action == 'accept':
            if req.status == 'pending':
                req.status = 'accepted'
                req.save()
                messages.success(request, f"Request from {req.renter.user.username} for '{req.property.name}' accepted.")
            else:
                messages.warning(request, "This request cannot be accepted at its current status.")

        elif action == 'reject':
            if req.status == 'pending':
                req.status = 'rejected'
                req.save()
                messages.info(request, f"Request from {req.renter.user.username} for '{req.property.name}' rejected.")
            else:
                messages.warning(request, "This request cannot be rejected at its current status.")
        else:
            messages.error(request, "Invalid action.")
        return redirect(f"{reverse('proprietordashboard')}?section=notifications")

    else:
        # On a GET request (when the user first visits the page),
        # the form is pre-populated with the existing data from 'user_profile'.
        form = ProfileEditForm(instance=user_profile, user=request.user)
        messages.error(request, "Invalid request method.")

    return redirect(f"{reverse('proprietordashboard')}?section=notifications")

@login_required
def renter_details(request, request_id):
    """
    Allows a proprietor to view the details of a renter who sent them a request.
    """
    current_user_profile = request.user.userprofile

    # 1. Ensure the logged-in user is a proprietor
    if current_user_profile.role != 'proprietor':
        messages.error(request, "Access Denied: Only proprietors can view renter details.")
        return redirect('home') # Redirect to a safe page if not a proprietor

    # 2. Get the specific Request object
    req = get_object_or_404(Request, id=request_id) #even not in model provided itself 

    # 3. Ensure the current proprietor is the proprietor of this specific request
    if req.proprietor != current_user_profile:
        messages.error(request, "Access Denied: You are not authorized to view details for this request.")
        return redirect('notifications') # Redirect back to notifications if not authorized

    # If authorized, get the renter's UserProfile
    renter_profile = req.renter

    context = {
        'renter_profile': renter_profile,
        'request_obj': req, # Pass the request object for context (e.g., property name)
        'property_obj': req.property, # Explicitly pass the property for convenience in template
    }
    return render(request, 'renter_details.html', context) # Use specific app template path

#for chatbox
def chat_view(request, request_id):
    req = get_object_or_404(Request, id=request_id)
    user_profile = request.user.userprofile

    # Ensure only related users can chat
    if req.status != 'accepted' or (user_profile != req.renter and user_profile != req.proprietor):
        django_messages.error(request, "Chat not available.")
        return redirect('notifications')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()

        if message_text:
            message = Message.objects.create(
                request=req,
                sender=request.user,
                text=message_text
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # Get the avatar URL correctly, using static function
                try:
                    avatar_url = message.sender.userprofile.profile_image.url
                except (AttributeError, ValueError):
                    # Handle cases where profile_image might be missing or userprofile doesn't exist
                    avatar_url = static('assets/images/default.png')

                return JsonResponse({
                    'status': 'success',
                    'message': {
                        'text': message.text,
                        'sender_is_current_user': message.sender == request.user,
                        'sender_avatar_url': avatar_url
                    }
                })
            
            return redirect('chat', request_id=request_id)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'error': 'Cannot send empty message.'})
            else:
                django_messages.error(request, "Cannot send empty message.")
                return redirect('chat', request_id=request_id)

    messages = Message.objects.filter(request=req)
    return render(request, 'chat.html', {
        'request_obj': req,
        'messages': messages,
        'user_role': 'renter' if user_profile == req.renter else 'proprietor',
    })

@login_required
def requests_view(request):
    """
    Shows pending and accepted requests for the logged-in user.
    """
    user_profile = request.user.userprofile
    
    # Pending requests: For both the renter (who sent it) and the proprietor (who receives it)
    pending_requests = Request.objects.filter(
        Q(renter=user_profile) | Q(proprietor=user_profile),
        status='pending'
    ).order_by('-id')

    # Accepted requests: For both the renter and the proprietor
    accepted_requests = Request.objects.filter(
        Q(renter=user_profile) | Q(proprietor=user_profile),
        status='accepted'
    ).order_by('-id')

    return render(request, 'requests.html', {
        'pending_requests': pending_requests,
        'accepted_requests': accepted_requests,
    })
