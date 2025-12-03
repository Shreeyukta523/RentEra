from django.shortcuts import render, redirect
import time
from rentals.forms import UserForm, UserProfileForm
from rentals.decorators import renter
from django.contrib import messages
from rentals.models import Request
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .models import UserActivity
from proprietor.models import Property
import re

from decimal import Decimal

# Create your views here.
@renter
def profile_page(request):
    section = request.GET.get("section", "profile")
    user = request.user
    user_profile = user.userprofile
    current_timestamp = int(time.time())
    inbox = None
    requests = None
    favourite = None
    sent_requets = None
    if section == "inbox":
        inbox = Message.objects.filter(sender=request.user)
    
    elif section == "requests":
      requests = Request.objects.filter(owner=request.user)   

    elif section == "favourite":
        favourite =Favourite.objects.filter(owner=request.user)

    elif section == "notifications":
        sent_requets = Request.objects.filter(renter=user_profile).order_by('-created_at')     

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
        'inbox': inbox,
        'requests': requests,
        'sent_requests': sent_requets,
        'favourite': favourite,
        'section': section,
    }
    return render(request, 'profile.html', context)

# WEIGHTS (can be tuned)
W_INTERACTION = Decimal("1.5")   # How strongly similar categories matter
W_PRICE       = Decimal("0.3")
W_LOCATION    = Decimal("0.8")
W_TYPE        = Decimal("0.6")

def get_recommendations(user, user_input):
    cutoff_date = timezone.now() - timedelta(days=30)

    recent_activities = UserActivity.objects.filter(
        user=user,
        timestamp__gte=cutoff_date
    ).select_related('property').order_by('-timestamp')[:10]

    # ===============================
    # BUILD USER CONTEXT
    # ===============================
    interacted_props = []
    recency_weights = {}

    total = recent_activities.count()
    if total > 0:
        for idx, act in enumerate(recent_activities):
            weight = Decimal("1") - (Decimal(idx) / Decimal(total))  # recent = 1.0, older lower
            interacted_props.append(act.property)
            recency_weights[act.property.id] = weight

    interacted_provinces = {p.province.lower() for p in interacted_props if p.province}
    interacted_districts = {p.District.lower() for p in interacted_props if p.District}
    interacted_municipalities = {p.Municipality.lower() for p in interacted_props if p.Municipality}
    interacted_wards = {str(p.ward_no).lower() for p in interacted_props if p.ward_no}
    interacted_types = {p.property_type.lower() for p in interacted_props if p.property_type}

    interacted_facilities = set()
    interacted_prices = []

    for p in interacted_props:
        if p.facilities.exists():
            interacted_facilities.update([f.name.lower() for f in p.facilities.all()])
        if p.price:
            interacted_prices.append(Decimal(p.price))

    avg_price = (sum(interacted_prices) / len(interacted_prices)) if interacted_prices else None

    combined_context = (user_input + " " +
                        " ".join(interacted_provinces |
                                 interacted_districts |
                                 interacted_municipalities |
                                 interacted_wards |
                                 interacted_types)).lower()

    all_props = Property.objects.filter(is_expired=False)
    scored = []

    for prop in all_props:

        # RECENCY WEIGHT (0–1)
        recency = recency_weights.get(prop.id, Decimal("0"))

        # SIMILARITY SCORE (independent of recency)
        interaction_score = Decimal("0")

        # Location similarity
        if prop.province and prop.province.lower() in interacted_provinces:
            interaction_score += Decimal("1")
            if prop.District and prop.District.lower() in interacted_districts:
                interaction_score += Decimal("1")
            if prop.Municipality and prop.Municipality.lower() in interacted_municipalities:
                interaction_score += Decimal("1")
            if prop.ward_no and str(prop.ward_no).lower() in interacted_wards:
                interaction_score += Decimal("1")

        # Type similarity
        type_similarity = Decimal("1") if (
            prop.property_type and prop.property_type.lower() in interacted_types
        ) else Decimal("0")

        # Facility similarity
        facility_similarity = Decimal("0")
        if prop.facilities.exists():
            prop_f = set(f.name.lower() for f in prop.facilities.all())
            facility_similarity = Decimal(len(prop_f & interacted_facilities))

        # Price similarity
        price_similarity = Decimal("0")
        if avg_price and prop.price:
            diff = abs(Decimal(prop.price) - avg_price)
            price_similarity = max(Decimal("0"), Decimal("2") - diff / Decimal("10000"))

        # Keyword similarity
        text = f"{prop.province} {prop.District} {prop.Municipality} {prop.ward_no} {prop.property_type}".lower()
        keyword_similarity = Decimal(sum(1 for w in combined_context.split() if w in text))

        # COMBINE USING PROPER WEIGHTS (NO recency yet!)
        similarity_score = (
            W_INTERACTION * interaction_score +
            W_PRICE       * price_similarity +
            W_LOCATION    * facility_similarity +
            W_TYPE        * type_similarity +
            keyword_similarity
        )

        # 4FINAL SCORE = similarity × recency weight (applied only once)
        final_score = similarity_score * (recency if recency > 0 else Decimal("0.05"))
        # If no recency, give a tiny boost 0.05 → allows new similar properties!

        if final_score > 0:
            scored.append((prop, final_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_recommendations = [p for p, _ in scored[:3]]

    if not top_recommendations:
        top_recommendations = list(all_props.order_by('-id')[:3])

    print("\n===== RECOMMENDATION DEBUG =====")
    print("User:", user.username)
    print("Interacted properties:")
    for p in interacted_props:
        print(" -", p.name)

    print("\nFinal Recommended properties:")
    for p in top_recommendations:
        print(" ->", p.name)
    print("================================\n")

    return top_recommendations

# individual property recommendations
def get_similar_properties(user, property_obj, limit=5):
    
    similar_props = Property.objects.filter(
        province=property_obj.province,
        District=property_obj.District,
        is_expired=False
    ).exclude(id=property_obj.id).prefetch_related('facilities')

    user_activities = UserActivity.objects.filter(
        user=user, property__in=similar_props
    )

    base_facilities = set(
        f.name.lower() for f in property_obj.facilities.all()
    )

    scored_props = []

    for prop in similar_props:
        score = 0

        if prop.Municipality == property_obj.Municipality:
            score += 5

            ward_diff = abs(prop.ward_no - property_obj.ward_no)
            if ward_diff == 0:
                score += 3
            elif ward_diff <= 2:
                score += 2
            elif ward_diff <= 5:
                score += 1
        
        if prop.property_type == property_obj.property_type:
            score+=2

        prop_facilities = set(
            f.name.lower() for f in prop.facilities.all()
        )
        matched_facilities = base_facilities & prop_facilities
        score += len(matched_facilities)

        price_diff = abs(prop.price - property_obj.price)
        if price_diff < 2000:
            score += 4
        elif price_diff < 5000:
            score += 3
        elif price_diff < 10000:
            score += 2
        elif price_diff < 20000:
            score += 1

        activity_count = sum(
            1 for act in user_activities if act.property_id == prop.id
        )
        score += activity_count * 2

        scored_props.append((prop, score))

    scored_props.sort(key=lambda x: x[1], reverse=True)

    return [prop for prop, score in scored_props[:limit]]


def parse_address(address):
    if not address:
        return {
            "ward_no": None,
            "city_or_tole": None,
            "raw_keywords": []
        }

    address = address.lower()

    # Extract ward number safely
    ward_match = re.search(r'(ward\s*\d+|\b\d+\b)', address)
    ward_no = None
    if ward_match:
        numbers = re.findall(r'\d+', ward_match.group())
        if numbers:
            ward_no = int(numbers[0])

    # Split into clean keywords (letters & digits only)
    raw_keywords = re.findall(r'[a-zA-Z]+|\d+', address)

    # First part is used as "city/tole" if exists
    city_or_tole = raw_keywords[0] if raw_keywords else None

    return {
        "ward_no": ward_no,
        "city_or_tole": city_or_tole,
        "raw_keywords": raw_keywords
    }

def get_address_based_recommendations(user):
    profile = user.userprofile
    user_address = profile.address or ""

    parsed = parse_address(user_address)
    ward_no = parsed["ward_no"]
    tole = parsed["city_or_tole"]
    keywords = parsed["raw_keywords"]

    all_props = Property.objects.filter(is_expired=False)
    scored = []

    for prop in all_props:
        score = 0

        location_text = f"{prop.province} {prop.District} {prop.Municipality} {prop.address}".lower()

        if prop.District and any(kw in prop.District.lower() for kw in keywords):
            score += 5

        if prop.Municipality and any(kw in prop.Municipality.lower() for kw in keywords):
            score += 4

        if ward_no and prop.ward_no == ward_no:
            score += 3

        if tole and prop.address and tole in prop.address.lower():
            score += 3

        # Keyword fallback (very soft match)
        score += sum(1 for kw in keywords if kw in location_text)

        if score > 0:
            scored.append((prop, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored[:3]]

def favourite_view(request):


    return render(request,'favourite.html')
