from django.shortcuts import render,redirect
from proprietor.forms import PropertyForm
from rentals.decorators import proprietor
from .models import Property, PropertyMedia
from .models import Land_number
# Create your views here.
from django.shortcuts import render, redirect
from django.forms import ValidationError
from .forms import PropertyForm
from .models import Land_number, UserProfile, Property # Ensure Property is imported
from django.shortcuts import render,redirect
from proprietor.forms import PropertyForm
from rentals.decorators import proprietor
from django.core.files import File

from django.shortcuts import redirect, render
from .models import Property
from rentals.models import UserProfile, Request
from django.http import JsonResponse
from django.db.models import Q

from rentals.models import Request, Message


import paypalrestsdk

#paypal
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings

from uuid import uuid4

from decimal import Decimal
from django.db.models.query import QuerySet
from django.core.files.uploadedfile import InMemoryUploadedFile

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from django.urls import reverse

from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMessage


from decimal import Decimal
import requests

import hmac
import hashlib
import base64
from django.conf import settings
from .forms import UserUpdateForm, UserProfileUpdateForm
from django.db.models import Max

#for paypal payment
paypalrestsdk.configure({
    "mode": "sandbox",  
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

def esewa_v2_generate_signature(message_str: str, secret_key: str) -> str:
    """
    Create HMAC-SHA256 signature and return base64 string.
    message_str must be the exact string eSewa expects (we use the same ordering below).
    """
    secret_bytes = secret_key.encode('utf-8')
    msg_bytes = message_str.encode('utf-8')
    sig = hmac.new(secret_bytes, msg_bytes, hashlib.sha256).digest()
    return base64.b64encode(sig).decode('utf-8')


@proprietor
def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            # Extract property and land details from the form
            cd = form.cleaned_data
            land_no_form = cd.get('land_no')
            sheet_no_form = cd.get('sheet_no')
            district_form = cd.get('District') # Ensure this matches your form field name casing
            ward_no_form = cd.get('ward_no')
            province_form = cd.get('province')
            municipality_form = cd.get('Municipality') # Ensure this matches your form field name casing
            address_form = cd.get('address') # Get address from form
            latitude_form = cd.get('latitude') # Get latitude from form
            longitude_form = cd.get('longitude') # Get longitude from form

            # Get the logged-in user's profile data
            user_profile = request.user.userprofile
            user_citizenship = user_profile.citizenship_number
            # Note: Accessing first_name/last_name from request.user directly
            # rather than user_profile if they are directly on the User model
            user_first_name = request.user.first_name # Assuming these are on the Django User model
            user_last_name = request.user.last_name   # Assuming these are on the Django User model

            # --- STEP 1: Check if the property already exists in the Property model ---
            # Define common fields to check for uniqueness for a property
            existing_property_check_query = Property.objects.filter(
                land_no=land_no_form,
                sheet_no=sheet_no_form,
                District=district_form,
                ward_no=ward_no_form,
                Municipality=municipality_form,
                province=province_form,
                # Consider if the same property can be listed by different users.
                # If only one user can list a specific property, add:
                # user_profile=user_profile,
            )

            if existing_property_check_query.exists():
                form.add_error(None, "This property (based on Land No, Sheet No, Coordinates, District, Ward, Municipality, Address, and Province) has already been listed.")
                return render(request, 'add_property.html', {'form': form})

            # --- STEP 2: Verify against Land_number records (as before) ---
            matching_land_records = Land_number.objects.filter(
                land_no=land_no_form,
                sheet_no=sheet_no_form,
                province=province_form,
                District=district_form,
                ward_no=ward_no_form,
                Municipality=municipality_form,
                first_name__iexact=user_first_name,
                last_name__iexact=user_last_name,
                citizenship_number=user_citizenship
            )

            if matching_land_records.exists():

                num_rooms = form.cleaned_data.get('number_of_rooms', 0)
                total_price = num_rooms * 100  # Rs. 100 per room       #RS. total price to display in the payment page
                total_price_usd = round(total_price/ 139.91, 2)         #for US currency in paypal

                cleaned_data = clean_for_session(form.cleaned_data.copy())

                # image = request.FILES['image']
                # image_name = image.name                                                 #large fields cant be stored in session, so we save the image temporarily in the default storage
                # temp_path = default_storage.save(f'temp_uploads/{uuid4()}_{image_name}', image) # storing images temporaily in default storage i.e. in folder tem_uploads for now, also used uuid so that the name of images donot collide
                media_files = request.FILES.getlist('file')
                temp_media = []
                for f in media_files:
                    temp_path = default_storage.save(f'temp_uploads/{uuid4()}_{f.name}', f)
                    temp_media.append({
                        'name': f.name,
                        'temp_path': temp_path
                    })
                request.session['property_data'] = {
                    'data': cleaned_data,
                    'total_price': total_price,
                    'total_price_usd': total_price_usd,  # Store USD price for PayPal
                    'media_files': temp_media
                    }
                return redirect('show_payment')
       
                # If a match is found in Land_number, it means the user is authorized to add this property.
                
            else:
                # If no matching Land_number record is found, inform the user.
                form.add_error(None, "The provided land details combined with your registered profile information do not match any existing land records. Property cannot be added as verified.")
                # You might choose to still save it with is_verified=False, or block it entirely.
                # For now, following your previous logic to block it if no match.
                return render(request, 'add_property.html', {'form': form})

        # If form is not valid (e.g., missing required fields in PropertyForm)
        return render(request, 'add_property.html', {'form': form})
    else:
        form = PropertyForm()
    return render(request, 'add_property.html', {'form': form})

# @proprietor
# def property_success(request):
#     return render(request, 'property_succ.html')

@proprietor
def proprietor_dashboard(request):
    user = request.user
    user_profile = request.user.userprofile
    section = request.GET.get("section", "profile")
    query = (request.GET.get('q') or "").strip()
    
# --- Profile Editing Logic ---
    if request.method == 'POST':
        # Ensure we bind forms to the current instances
        user_form = UserUpdateForm(request.POST, instance=request.user)
        user_profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user.userprofile)

        if user_form.is_valid() and user_profile_form.is_valid():
            
            # --- FINAL, ROBUST FIX: Preserve Name and Email Data ---
            
            # 1. Get the original user object directly from the database to ensure its values are current.
            # (We use request.user.pk to get the primary key)
            original_user = User.objects.get(pk=request.user.pk)
            
            # 2. Save the User form, but DON'T commit to the database yet.
            user_instance = user_form.save(commit=False) 
            
            # 3. Manually reset the non-editable fields using the original, saved values.
            # This overwrites the empty/cleared values submitted by the form.
            user_instance.first_name = original_user.first_name
            user_instance.last_name = original_user.last_name
            user_instance.email = original_user.email
            
            # 4. Save the User instance with the preserved data.
            user_instance.save() 
            
            # 5. Save the Profile form.
            user_profile_form.save()
            
            # Redirect to the profile section after successful save
            return redirect(f'{request.path}?section=profile')
    else:
        # GET Request: Populate forms with existing data
        user_form = UserUpdateForm(instance=user)
        user_profile_form = UserProfileUpdateForm(instance=user_profile)
    # -----------------------------

    # Default empty values
    properties = Property.objects.none()
    backup_properties=Property.objects.none()
    inbox = None
    renter_lists = None
    pending_requests = Request.objects.none()
    accepted_requests = Request.objects.none()
    received_requests = Request.objects.none()

    selected_messages = None
    active_request_id = None

    # === SECTION HANDLERS === #

    if section == "inbox":
        latest_per_request = (
            Message.objects.filter(request__proprietor=user_profile, request__status="accepted")
            .values("request")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )

        inbox = (
            Message.objects.filter(id__in=latest_per_request)
            .select_related("sender", "request", "request__property")
            .order_by("-timestamp")
        )

        req_id = request.GET.get("chat")
        active_request_id = int(req_id) if req_id else None
        selected_messages = Message.objects.filter(request_id=active_request_id) if active_request_id else None

    elif section == "requests":
        pending_requests = Request.objects.filter(
            proprietor=user_profile, status="pending"
        ).order_by("-created_at")

        accepted_requests = Request.objects.filter(
            proprietor=user_profile, status="accepted"
        ).order_by("-created_at")

    elif section == "renter_lists":
        renter_lists = RenterList.objects.filter(owner=user_profile)

    elif section == "notifications":
        received_requests = Request.objects.filter(
            proprietor=user_profile
        ).order_by("-created_at")

    elif section == "properties":
        base_qs = Property.objects.filter(user_profile=user_profile, is_expired=False)

        if query:
            properties = base_qs.filter(
                Q(name__icontains=query) |
                Q(address__icontains=query)
            ).order_by("-created_at")
        else:
            properties = base_qs.order_by("-created_at")

    elif section == "backup_properties":
        base_backup_qs = Property.objects.filter(user_profile=user_profile, is_expired=True)

        if query:
            backup_properties = (
                base_backup_qs
                .filter(
                    Q(name__icontains=query) |
                    Q(address__icontains=query)
                )
                .order_by('-created_at')
            )
        else:
            backup_properties = base_backup_qs.order_by('-created_at')

    context = {
        'properties': properties,
        'backup_properties': backup_properties, 
        'inbox': inbox,
        'selected_messages': selected_messages,
        'active_request_id': active_request_id,
        'pending_requests': pending_requests,
        'accepted_requests': accepted_requests,
        'renter_lists': renter_lists,
        'received_requests': received_requests,
        'query': query,
        'section': section,

    }

    return render(request, 'prop_dashboard.html', context)
#django model produces objects like decimal.decimal, queryset etc but while storring in sessiio it first must be serialized before storing it in cookie or session
#as builtin json encoder only understands limited sets of types: str, int, float, bool, None, list, dict, while django produces query sets, bytes which is not json serializable so it must first be converted.
def clean_for_session(data):
    if isinstance(data, dict):
        return {k: clean_for_session(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_session(i) for i in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, QuerySet):
        return list(data.values_list('id', flat=True))
    elif isinstance(data, InMemoryUploadedFile):
        return data.name  # only store filename
    elif isinstance(data, bytes):
        return None  # skip or replace bytes
    else:
        return data

@proprietor
def property_success(request):
    data = request.session.get('property_data')
    if not data:
        return redirect('addproperty')

    transaction_uuid = request.GET.get('transaction_uuid')

    if transaction_uuid:   # eSewa success
        esv = request.session.get('esewaverify')
        if not esv:
            return redirect('propertycancel')

        verify_payload = {
            "product_code": settings.ESEWA_PRODUCT_CODE,
            "transaction_uuid": esv.get('transaction_uuid'),
            "total_amount": esv.get('total_amount'),
        }

        try:
            resp = requests.post(settings.ESEWA_V2_VERIFY_URL, json=verify_payload, timeout=10)
            resp_json = resp.json()

            if resp_json.get("status") != "COMPLETE":
                return redirect('propertycancel')

        except Exception:
            return redirect('propertycancel')
        
    elif request.GET.get("paymentId") and request.GET.get("PayerID"):

        payment_id = request.GET["paymentId"]
        payer_id = request.GET["PayerID"]

        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            if not payment.execute({"payer_id": payer_id}):
                return redirect("propertycancel")
        except Exception:
            return redirect("propertycancel")

    elif request.GET.get("PayerID"):
        
        pass


    user_profile = request.user.userprofile

    # Restore expired property
    if 'restore_property_id' in data:
        try:
            prop = Property.objects.get(id=data['restore_property_id'], user_profile=user_profile)
        except Property.DoesNotExist:
            return redirect('proprietor_dashboard')

        now = timezone.now()
        prop.is_expired = False
        prop.expires_at = now + timedelta(days=30)
        prop.backup_expires_at = prop.expires_at + timedelta(minutes=5)
        prop.save(update_fields=['is_expired', 'expires_at', 'backup_expires_at'])

        del request.session['property_data']
        return render(request, 'property_succ.html', {'property': prop})

    form_data = data['data']
    media_files = data.get('media_files', [])

    property_instance = Property.objects.create(
        user_profile=user_profile,
        name=form_data['name'],
        province=form_data['province'],
        address=form_data['address'],
        District=form_data['District'],
        ward_no=form_data['ward_no'],
        Municipality=form_data['Municipality'],
        price=form_data['price'],
        property_type=form_data['property_type'],
        number_of_rooms=form_data['number_of_rooms'],
        description=form_data['description'],
        land_no=form_data['land_no'],
        sheet_no=form_data['sheet_no'],
        latitude=form_data['latitude'],
        longitude=form_data['longitude'],
        is_verified=True,
    )

    for m in media_files:
        temp_path = m['temp_path']
        if default_storage.exists(temp_path):
            with default_storage.open(temp_path, 'rb') as f:
                PropertyMedia.objects.create(
                    property=property_instance,
                    file=File(f, name=m['name'])
                )
            default_storage.delete(temp_path)

    if 'property_data' in request.session:
        del request.session['property_data']

    return render(request, 'property_succ.html', {'property': property_instance})

@proprietor
def property_cancel(request):
    return render(request, "payfail.html")

''' 
@proprietor
def show_payment(request):
    data = request.session.get('property_data')
    if not data:
        return redirect('addproperty')

    amt = str(data['total_price'])
    pid = str(uuid4())  # same as working code

    esewa_fields = {
        'amt': amt,
        'psc': '0',
        'pdc': '0',
        'txAmt': '0',
        'tAmt': amt,
        'pid': pid,
        'scd': settings.ESEWA_MERCHANT_ID,
        'su': request.build_absolute_uri(reverse('propertysuccess')),
        'fu': request.build_absolute_uri(reverse('propertycancel')),
    }

    # MUST match what you read later!
    request.session['esewaverify'] = {
        'pid': pid,
        'amt': amt,
    }

    return render(request, "show_pay.html", {
        'esewa_fields': esewa_fields,
        'paypal_form': PayPalPaymentsForm(initial={
            "cmd": "_xclick",
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "amount": str(data['total_price_usd']),
            "item_name": "Property Listing Fee",
            "invoice": str(uuid4()),
            "currency_code": "USD",
            "notify_url": request.build_absolute_uri("/paypal-ipn/"),
            "return_url": request.build_absolute_uri(reverse('propertysuccess')),
            "cancel_return": request.build_absolute_uri(reverse('propertycancel')),
        }),
        'total_price': data['total_price'],
        'esewa_payment_url': settings.ESEWA_BASE_URL,
    })
 '''

@proprietor
def show_payment(request):
    data = request.session.get('property_data')
    if not data:
        return redirect('addproperty')

    # Amounts
    total_amount = str(data['total_price'])             # NPR amount (string)
    tax_amount = "0"
    # transaction UUID for this payment
    transaction_uuid = str(uuid4())

    # product_code and secret key from settings
    product_code = settings.ESEWA_MERCHANT_ID
    secret_key = settings.ESEWA_SECRET_KEY

    # Build the message string exactly in this order (required for signature)
    # ORDER: total_amount,transaction_uuid,product_code
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"

    signature = esewa_v2_generate_signature(message, secret_key)

    # eSewa v2 fields
    esewa_fields = {
        "amount": total_amount,                      # product amount
        "tax_amount": tax_amount,
        "product_delivery_charge": "0",
        "product_service_charge": "0",
        "total_amount": total_amount,                # amount + taxes
        "transaction_uuid": transaction_uuid,
        "product_code": product_code,
        "success_url": request.build_absolute_uri(reverse('propertysuccess')),
        "failure_url": request.build_absolute_uri(reverse('propertycancel')),
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": signature,
    }

    # Save minimal verification info in session for later verification
    request.session['esewaverify'] = {
        'transaction_uuid': transaction_uuid,
        'total_amount': total_amount,
    }

    # Render template (PayPal logic remains unchanged)
    return render(request, "show_pay.html", {
        'esewa_fields': esewa_fields,
        'esewa_payment_url': settings.ESEWA_V2_PAYMENT_URL,
        'paypal_form': PayPalPaymentsForm(initial={
            "cmd": "_xclick",
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "amount": str(data['total_price_usd']),
            "item_name": "Property Listing Fee",
            "invoice": str(uuid4()),
            "currency_code": "USD",
            "notify_url": request.build_absolute_uri("/paypal-ipn/"),
            "return_url": request.build_absolute_uri(reverse('propertysuccess')),
            "cancel_return": request.build_absolute_uri(reverse('propertycancel')),
        }),
        'total_price': data['total_price'],
    })


@proprietor
def delete_property(request, slug):
    if request.method == 'POST':
        try:
            prop = Property.objects.get(slug=slug, user_profile=request.user.userprofile)
            prop.expires_at = timezone.now()
            prop.backup_expires_at = prop.expires_at + timedelta(minutes=10)
            prop.is_expired=True
            prop.save(update_fields=['is_expired'])
            return JsonResponse({'success': True})
        
        except Property.DoesNotExist:
            return JsonResponse({'success': False}, status=404)

    return JsonResponse({'success': False}, status=405)

@proprietor
def restore_property_request(request, property_id):
    try:
        prop=Property.objects.get(id=property_id, user_profile=request.user.userprofile, is_expired=True)

    except Property.DoesNotExist:
        return redirect('proprietor_dashboard')
    
    num_rooms=prop.number_of_rooms or 1
    total_price=num_rooms * 100
    total_price_usd=round(total_price/139.91,2)

    #saving property in session until payment
    #including current property date
    property_data={
        'data' : {
            'name' :prop.name,
            'province':prop.province,
            'address':prop.address,
            'Municipality':prop.Municipality,
            'District':prop.District,
            'latitude': prop.latitude,
            'longitude': prop.longitude,
            'ward_no': prop.ward_no,
            'price': prop.price,
            'property_type': prop.property_type,
            'number_of_rooms': prop.number_of_rooms,
            'description': prop.description,
            'sheet_no': prop.sheet_no,
            'land_no': prop.land_no,
        },
        'total_price':total_price,
        'total_price_usd':total_price_usd,
        'restore_property_id':prop.id,          #marking it as restore
    }
    request.session['property_data']=clean_for_session(property_data)
    return redirect('show_payment')


