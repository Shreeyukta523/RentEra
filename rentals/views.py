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

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import joblib
import os

from rest_framework.authentication import BasicAuthentication # Or others
from rest_framework.permissions import AllowAny
from renter.views import get_recommendations, get_similar_properties,get_address_based_recommendations
from renter.models import UserActivity

from django.utils import timezone
from datetime import timedelta


def home(request):
    """
    View for the homepage (index.html).
    Uses 'is_verified=True' instead of 'is_featured=True'.
    """
    property_types = Property.objects.values_list('property_type', flat=True).distinct()
    
    default_type = 'House' 
    if default_type not in property_types:
        default_type = property_types.first() if property_types else None

    # Filter by is_verified=True (assuming verified properties are featured)
    initial_properties = Property.objects.filter(
        is_verified=True,  # <-- CORRECTED FIELD
        property_type=default_type
    ).prefetch_related('facilities').order_by('?') 

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

    recommended_props = []

    # 🔥 SINGLE UNIFIED CHECK
    if request.user.is_authenticated and getattr(request.user, "userprofile", None) and request.user.userprofile.role == "renter":
        
        # 1️⃣ Try behavior-based recommendations
        new_recommendations = get_recommendations(
            user=request.user,
            user_input=search
        )

        # 2️⃣ Check interaction count
        interaction_count = UserActivity.objects.filter(
            user=request.user,
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).count()

        if interaction_count == 0:
            new_recommendations = get_address_based_recommendations(request.user)

        recommended_props = new_recommendations

    context = {
        'property_types': property_types,
        'initial_properties': initial_properties,
        'default_property_type': default_type,
        'recommended_props': recommended_props
    }
    return render(request, 'index.html', context)


# =======================================================
# 2.  AJAX VIEW (Filter/Carousel) - CORRECTED
# =======================================================
def get_featured_properties(request):
    """
    AJAX view to fetch properties as JSON.
    This version is corrected based on the Property model.
    """
    property_type = request.GET.get('type')
    
    # Base query for all verified properties
    properties_queryset = Property.objects.filter(
        is_verified=True
    )

    # If a type is given (e.g., "house"), filter by it
    if property_type:
        properties_queryset = properties_queryset.filter(
            property_type=property_type
        )
    # If no type is given (the "All" button), we get all properties
    
    properties_queryset = properties_queryset.order_by('?').prefetch_related('facilities')

    properties_list = []
    for prop in properties_queryset:
        facilities = [facility.name for facility in prop.facilities.all()]
        
        properties_list.append({
            'name': prop.name,
            'slug': prop.slug,
            'image_url': prop.main_image() if prop.main_image() else None,
            
            # --- THIS IS THE CORRECTED LINE ---
            # Your Property model has no 'sale_rent_status' field.
            # We will hardcode "For Rent" as this appears to be a rental-only site.
            'sale_rent_status': 'For Rent',
            # ----------------------------------
            
            'price': f"{prop.price:,.0f}", 
            
            # This is also correct, your model has 'number_of_rooms'
            'rooms': prop.number_of_rooms or 1, 
            
            'facilities': facilities,
        })
    
    return JsonResponse({'properties': properties_list})


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
from django.db.models import Q

def property_view(request):
    properties_list = Property.objects.filter(is_expired=False).order_by('-created_at')

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
        properties_list = properties_list.filter(
            Q(name__icontains=search) | Q(address__icontains=search)
        )
        selected_filters.update({k: '' if k != 'search' else search for k in filters.keys()})
    else:
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
    
    recommended_props = []

    # 🔥 SINGLE UNIFIED CHECK
    if request.user.is_authenticated and getattr(request.user, "userprofile", None) and request.user.userprofile.role == "renter":
        
        # 1️⃣ Try behavior-based recommendations
        new_recommendations = get_recommendations(
            user=request.user,
            user_input=search
        )

        # 2️⃣ Check interaction count
        interaction_count = UserActivity.objects.filter(
            user=request.user,
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).count()

        # 3️⃣ Fallback to location/address recommendations
        if interaction_count == 0:
            new_recommendations = get_address_based_recommendations(request.user)

        # 🔥 DEBUG: PRINT IF CHANGED
        print("\n===== RECOMMENDATION DEBUG =====")
        print(f"Total interactions (30 days): {interaction_count}")
        print("New recommendations:")
        for p in new_recommendations:
            print(" ->", p.name)
        print("================================\n")

        recommended_props = new_recommendations

    context = {
        'properties': properties,
        'property_types': property_types,
        'facilities': facilities,
        'PROVINCES': PROVINCES,
        'selected_filters': selected_filters,
        'recommended_props': recommended_props,
    }

    return render(request, 'properties.html', context)

def propertydetails(request, slug):
    if not request.user.is_authenticated:
        return redirect('login')

    property_obj = get_object_or_404(Property, slug=slug)
    user_profile = request.user.userprofile
    is_proprietor = (user_profile.role == 'proprietor')

    renter_has_pending_request = False
    renter_has_accepted_request = False
    renter_has_rejected_request = False
    renter_has_cancelled_request = False

    current_pending_request = None
    current_accepted_request = None
    current_rejected_request = None
    current_cancelled_request = None

    # 🔥 SINGLE CHECK
    if user_profile.role == 'renter':

        # Save activity (this automatically increases count)
        UserActivity.objects.create(
            user=request.user,
            property=property_obj
        )

        interactions = UserActivity.objects.filter(
            user=request.user,
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).order_by('-timestamp')

        print("\n===== USER ACTIVITY DEBUG =====")
        print(f"User: {request.user.username}")
        print("Recent interactions:")
        for ia in interactions:
            print(f" -> {ia.property.name}  at  {ia.timestamp}")
        print("================================\n")

        current_pending_request = Request.objects.filter(
            renter=user_profile, property=property_obj, status='pending'
        ).order_by('-created_at').first()

        if current_pending_request:
            renter_has_pending_request = True

        current_accepted_request = Request.objects.filter(
            renter=user_profile, property=property_obj, status='accepted'
        ).order_by('-created_at').first()
        if current_accepted_request:
            renter_has_accepted_request = True

        current_rejected_request = Request.objects.filter(
            renter=user_profile, property=property_obj, status='rejected'
        ).order_by('-created_at').first()
        if current_rejected_request:
            renter_has_rejected_request = True

        current_cancelled_request = Request.objects.filter(
            renter=user_profile, property=property_obj, status='cancelled'
        ).order_by('-created_at').first()
        if current_cancelled_request:
            renter_has_cancelled_request = True

    similar_props = get_similar_properties(request.user, property_obj, limit=3) if request.user.is_authenticated else []

    context = {
        'property': property_obj,
        'is_proprietor': is_proprietor,
        'renter_has_pending_request': renter_has_pending_request,
        'current_pending_request': current_pending_request,
        'renter_has_accepted_request': renter_has_accepted_request,
        'current_accepted_request': current_accepted_request,
        'renter_has_rejected_request': renter_has_rejected_request,
        'current_rejected_request': current_rejected_request,
        'renter_has_cancelled_request': renter_has_cancelled_request,
        'current_cancelled_request': current_cancelled_request,
        'similar_props': similar_props,
    }
    return render(request, 'property_details.html', context)

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
    """ referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'requests') """

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

@login_required
def manage_request(request, request_id, action):
    req = get_object_or_404(Request, id=request_id)
    user_profile = request.user.userprofile

    # Ensure only the proprietor of this request can manage it
    if req.proprietor != user_profile:
        messages.error(request, "You are not authorized to manage this request.")
        # Redirect to requests section as default
        return redirect(f"{reverse('proprietordashboard')}?section=requests")

    if request.method == 'POST':
        # Accept or Reject logic
        if action == 'accept' and req.status == 'pending':
            req.status = 'accepted'
            req.save()
            messages.success(request, f"Request from {req.renter.user.username} for '{req.property.name}' accepted.")
        elif action == 'reject' and req.status == 'pending':
            req.status = 'rejected'
            req.save()
            messages.info(request, f"Request from {req.renter.user.username} for '{req.property.name}' rejected.")
        else:
            messages.warning(request, "This request cannot be processed at its current status.")

        # Use 'next' parameter to redirect dynamically
        next_url = request.POST.get('next')  # e.g., ?section=requests or ?section=notifications
        if next_url:
            return redirect(f"{reverse('proprietordashboard')}{next_url}")
        # Fallback to requests section
        return redirect(f"{reverse('proprietordashboard')}?section=requests")

    # If the request is GET or invalid method, just redirect back to dashboard safely
    messages.error(request, "Invalid request method.")
    return redirect(f"{reverse('proprietordashboard')}?section=requests")

    """ referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'requests') """


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



# --- 1. Knowledge Base (Static Answers) ---
# The NLP model predicts a key (intent), and we look up the answer here.
STATIC_RESPONSES = {
    # 1. General Conversational Intents
    # UPDATED GREETING with new persona: "RenTera AI Chatbot"
    "greeting": "Hello! Welcome to RenTera, your safe rental platform! I'm your **RenTera AI Chatbot**. How can I help you find your next great space today? 😊",
    "goodbye": "It was a pleasure assisting you! Happy home searching, and come back to RenTera anytime. Safe travels! 👋",
    "thanks": "You're very welcome! I'm here to make your rental journey easier. Let me know if anything else pops up! 🙏",
    "general_help": "I can help with questions about: **Listing Fees (Proprietors)**, **Renter Costs (Free!)**, **Platform Features**, **Login/Signup**, and **Safety Verification**. What's on your mind? 💡",
    
    # 2. RenTera Specific Intents (Financial)
    "pricing_proprietor": "Welcome, proprietor! Listing your space is easy: it's a flat **₹100 per room**, active for a full **3 months**. That's a great value for prime visibility! 🏡✨",
    "pricing_renter": "Fantastic news! **Finding your dream home on RenTera is completely free for renters!** No hidden fees or commissions. Search, filter, and connect freely. 🥳",
    
    # 3. RenTera Specific Intents (Features & Access)
    "features_platform": "We offer powerful **filtering**, direct **in-app chat** with owners, and detailed property views including basics (parking, water) and the **exact map location**. Everything you need! 🗺️💬",
    "safety_verification": "Safety first! We verify all users. Proprietors submit **land numbers** and documents; renters provide **citizenship verification**. We keep RenTera secure and trustworthy. ✅🔒",
    "report_issue": "Oh no! I'm sorry you've encountered an issue. Please describe the problem (e.g., *broken chat feature*, *inappropriate listing*), and I'll direct you to a human support agent immediately. 🚨",

    # 4. Expanded Access and Onboarding Intents
    "account_access": "To ensure safety and unlock full details (like owner chat/contact), please complete a quick **Sign Up or Log In**. Look for the 'Register' button at the top right! 🔑💻",
    "onboarding_process": "Starting your RenTera journey is simple! First, use our search and filters. Once you find 'the one,' **Log In**, and click 'Send Request' to start a direct chat with the proprietor. Happy searching! 🚀"
}

# --- 2. Load the Trained Model and Vectorizer ---
# The model is loaded once when the Django server starts.
INTENT_MODEL = None
try:
    # Construct the absolute path to the model file
    app_dir = os.path.dirname(__file__)
    model_path = os.path.join(app_dir, 'intent_model.joblib')
    
    # Load the entire trained pipeline (Vectorizer + Classifier)
    INTENT_MODEL = joblib.load(model_path)
    print("Custom NLP Intent Model loaded successfully.")
except Exception as e:
    # This error handles the case where the model file is missing (i.e., train_model.py wasn't run)
    print(f"FATAL ERROR: Failed to load INTENT_MODEL. Did you run 'python rentals/train_model.py'? Error: {e}")
    INTENT_MODEL = None


# --- 3. The Predict Function ---
def predict_intent(user_message: str) -> str:
    """Uses the loaded model to predict the user's intent."""
    if INTENT_MODEL:
        # Predict the intent (e.g., 'pricing', 'features') from the user's message
        return INTENT_MODEL.predict([user_message.lower().strip()])[0]
    return "error"


# --- 4. The Django View ---
# Django is designed to be highly secure. By default, every time your Django server receives a request that changes data (like a POST request, which sends the user's message), it requires a hidden security token called a CSRF token.
# "For this specific view, I know the risks, and I am allowing external POST requests to bypass the mandatory CSRF token check."



# CSRF exemption is needed to allow AJAX POST requests from the frontend.
@method_decorator(csrf_exempt, name='dispatch')
class AIChatView(APIView):
    """
    Django REST Framework View that uses the custom-trained NLP model.
    """
    authentication_classes = [BasicAuthentication] 
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message', '').strip()
#         : When the user's browser sends the chat message to your server, it packages the message inside the HTTP request's body, usually as a JSON object that looks something like this: {"message": "What are your features?"}. The request.data object in Django REST Framework is responsible for reading and parsing this content.

# .get('message', ''): This is a robust way to retrieve the value associated with the key 'message' from the data.
        if not user_message:
            return Response({"ai_response": "Please provide a message to the chatbot."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        # Ensure the model is loaded before attempting prediction
        if INTENT_MODEL is None:
             return Response(
                {"ai_response": "The Custom AI Model failed to load on the server. Please check the server logs. 😥"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            # CLASSIFY: Predict the user's intent
            intent = predict_intent(user_message)
            
            # GENERATE: Look up the response based on the predicted intent
            if intent in STATIC_RESPONSES:
                ai_response = STATIC_RESPONSES[intent]
            else:
                # Fallback for irrelevant questions
                ai_response = (
                    "I am a custom-trained guide. I can only discuss our **pricing, features, contact, or navigation**. "
                    "I don't understand that request. 🤔"
                )

            # CONSTRUCT RESPONSE
            return Response({
                "ai_response": ai_response, 
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # General server error handling
            print(f"General Server Error during prediction: {e}")
            return Response(
                {"ai_response": "A critical server error occurred while processing my custom logic. 😟"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
from django.contrib.auth import get_user_model, update_session_auth_hash
# Change this:
# from django.contrib.auth.forms import PasswordChangeForm 

from django.contrib.auth.forms import SetPasswordForm
from django.core.mail import send_mail
from django.contrib import messages
from django.urls import reverse
from .models import PasswordResetOTP # Import the model
from django.contrib.auth.decorators import login_required # Used for session access

# Get the custom or default User model
User = get_user_model()#When you use the code User = get_user_model(), the resulting User variable represents the database table that stores all your user records.

# --- Step 1: Request Email/Username and Send OTP ---
def password_reset_request(request):
    if request.method == 'POST':
        if 'password_reset_user_id' in request.session:#clearingtheprevsessiondata
            del request.session['password_reset_user_id']
        email_or_username = request.POST.get('email_or_username', '').strip()
        #that removes leading and trailing whitespace (spaces, tabs, newlines).
        try:
            # Try finding by email (case-insensitive)
            user = User.objects.get(email__iexact=email_or_username)
        except User.DoesNotExist:#use.doesnotexist. isthe. error. efined
            try:
                # If not found by email, try by username (case-insensitive),uses functions like LOWER() on both sides of the comparison.
                user = User.objects.get(username__iexact=email_or_username)
            except User.DoesNotExist:
                # Security best practice: Redirect to a 'done' page 
                # to avoid revealing whether a user exists or not.
                
                return redirect('password_reset_otp_done')

        # 1. Generate and Save/Update OTP. 
        otp_instance, created = PasswordResetOTP.objects.get_or_create(user=user)
        otp_instance.generate_otp() #so if the user tries to forget psw again and agian the otp object is just updated with new otp 

# and during creation the save fn runs so expiry date is set to +5 mins and again .generate sets the expiry date and replace with +5 of when second line runs
#f within 5 mins of otp generation , new otp is requested then the otp feild is chnaged then prev otp doesn't work
        # 2. Send Email with OTP
        subject = 'Your Password Reset OTP Code'
        message = (f'Hello {user.username},\n\n'
                   f'Your One-Time Password for resetting your password is: {otp_instance.otp_code}\n'
                   f'This code will expire in 5 minutes.\n\n'
                   'If you did not request a password reset, please ignore this email.')
                   
        send_mail(
            subject, 
            message, 
            'no-reply@yourdomain.com', # Use a valid sender email. Django checks your settings.py for the EMAIL_BACKEND setting. This setting tells Django how to process the email.
            [user.email],
            fail_silently=False,
        )

        # Use the session to temporarily store the user's ID for the verification step
        request.session['password_reset_user_id'] = user.id
        # so in this session we are storing a key value , so session lets to add a key value pair that can retrived during that session in different pages and cureenlt we are not logged in so to store we have to add a new key value pair to store the info otherwise during logged in state the middlewares handle this and store it in session ??
        
        # 3. Redirect to the OTP verification page
        return redirect('password_reset_verify_otp')

    return render(request, 'password_reset_request.html')#is called ifthe request isnot post.

def password_reset_otp_done(request):
    """Simple confirmation page after sending the OTP."""
    return render(request, 'password_reset_otp_done.html')


# --- Step 2: Verify OTP Code ---
def password_reset_verify_otp(request):
    # Check if a user ID is stored in the session
    user_id = request.session.get('password_reset_user_id')#retriving theinfofromthesession
    print(user_id)
    if not user_id:
        messages.error(request, 'Password reset flow interrupted. Please start over.')
        return redirect('password_reset_otp_request')
        
    try:
        user = User.objects.get(id=user_id)
        otp_instance = PasswordResetOTP.objects.get(user=user)
    except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
        messages.error(request, 'Invalid request. Please start over.')
        return redirect('password_reset_otp_request')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code', '').strip()
        
        if otp_instance.is_valid() and entered_otp == otp_instance.otp_code:
            # OTP is valid! Grant access to the final reset form.
            request.session['otp_verified'] = True
            # The session ID remains for the final step
            return redirect('password_reset_new_password')
        
        else:
            messages.error(request, 'Invalid or expired OTP code.')
            # Optional: Allow resend logic here
            
    # Remove the OTP code from the instance before rendering the form 
    # for security if it was accessed directly
    
    return render(request, 'password_reset_verify_otp.html', {'user': user})


# --- Step 3: Set New Password ---
def password_reset_new_password(request):
    """
    Handles the final step of the password reset flow: setting the new password.
    Requires 'otp_verified' flag and 'password_reset_user_id' in the session.
    """
    
    # 1. Check session flags from verification step
    if not request.session.get('otp_verified'):
        messages.error(request, 'Verification required. Please verify the OTP first.')
        return redirect('password_reset_verify_otp')

    user_id = request.session.get('password_reset_user_id')
    
    # 2. Retrieve the user object
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # If the user somehow disappeared, clear session and start over
        if 'password_reset_user_id' in request.session:
            del request.session['password_reset_user_id']
        messages.error(request, 'User not found. Please start the process again.')
        return redirect('password_reset_otp_request')

    # 3. Handle Form Submission (POST)
    if request.method == 'POST':
        #  FIX: Use SetPasswordForm. It only needs new_password1/2 and knows the user.
        form = SetPasswordForm(user=user, data=request.POST)#creating. insyance. of. the. class form = SetPasswordForm(user=user, data=request.POST) 
#         The SetPasswordForm class is designed to look for specific keys in the data dictionary (which is request.POST).
#so. the. namesshould. be. fixed. that. can. berecognised. by. the. setpswdclass
# It typically expects a field for the new password (often named new_password1).

# It expects a field for confirmation (often named new_password2).

# Django's Forms system automatically matches the keys in request.POST (e.g., 'new_password1') to the field names defined within the SetPasswordForm class.

# If your HTML uses the expected name attributes (like new_password1 and new_password2), the form is populated correctly and can proceed with validation.
        if form.is_valid():
            # This calls user.set_password(new_password) and user.save()
            form.save()#conduct. the. comp.are ,weak. check. missing. check. and. is. attaches. the. error. with. form. object
            
            # Clean up: Delete the OTP instance from the database
            PasswordResetOTP.objects.filter(user=user).delete()
            
            # Clean up: Clear the temporary session flags
            if 'otp_verified' in request.session:
                 del request.session['otp_verified']
            if 'password_reset_user_id' in request.session:
                 del request.session['password_reset_user_id']
            
            messages.success(request, 'Your password has been successfully set. Please log in.')
            return redirect('login') 

    # 4. Handle Initial Form Display (GET)
    else:
        # 🔑 FIX: Use SetPasswordForm. It correctly renders only new_password1/2.
        form = SetPasswordForm(user=user)

    return render(request, 'password_reset_new_password.html', {'form': form})##if. invalid. form. thenrenders. through. this.
