from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from django.contrib.sites.shortcuts import get_current_site

def send_expiry_warning_email(property_obj, request):
    user = property_obj.user_profile.user
    property_name = property_obj.name
    expiry_date = property_obj.expires_at.strftime("%Y-%m-%d %H:%M:%S")

    # Optional — if you have a restore link or dashboard link
    current_site = get_current_site(request)
    dashboard_link = f"http://{current_site}/dashboard?section=backup_properties"

    email_subject = f"Reminder: Your property '{property_name}' will expire soon!"
    email_body = render_to_string('property_expiry_email.html', {
        'user': user,
        'property_name': property_name,
        'expiry_date': expiry_date,
        'dashboard_link': dashboard_link
    })

    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email='krishalasth34@gmail.com',
        to=[user.email],
    )
    email.content_subtype = "html"
    email.send()
