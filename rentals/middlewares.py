from django.shortcuts import redirect
from django.conf import settings

from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.deprecation import MiddlewareMixin
from importlib import import_module


from django.utils import timezone
from proprietor.models import Property

from datetime import timedelta
import os
from django.utils.text import slugify


from django.core.mail import EmailMessage
from django.template.loader import render_to_string


# Middleware to handle authentication and guest access
#Django stores session data on the server-side—not inside the cookie itself. The cookie only contains the session key (sessionid, user_sessionid, etc.).
#Exactly! In Django, middleware methods like process_request() and process_response() are hooks that run before and after each view function on every HTTP request.
#The middleware execution flow is handled deep inside Django’s core request/response handling,


#if not logged in redirect to login page
#Authenticated users only
def auth(view_function):
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  
        return view_function(request, *args, **kwargs)
    return wrapped_view

#if logged in redirect to  logout page
# ********Guest*******
# Guests only (unauthenticated users)
def guest(view_function):
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('myprofile')  
        return view_function(request, *args, **kwargs)
    return wrapped_view


#to seperate admin and user sessions so they donot collide
# class CustomSessionCookieMiddleware(MiddlewareMixin):
#     def process_request(self, request): #process_request() — called before your view function runs.

# #process_response() — called after your view returns a response.
#         # Use different cookie names based on URL
#         if request.path.startswith('/admin/'):
#             cookie_name = 'admin_sessionid'
#         else:
#             cookie_name = 'user_sessionid'

#         engine = import_module(settings.SESSION_ENGINE)#Dynamically imports Django’s session backend (e.g., django.contrib.sessions.backends.db). This is the module that handles session data storage.
#         session_key = request.COOKIES.get(cookie_name)#Extracts the session ID from the appropriate cookie (admin_sessionid or user_sessionid).
#         request.session = engine.SessionStore(session_key)#Initializes the session using that session key. If it's None, a new session is started.
#         request._session_cookie_name = cookie_name#Stores which cookie name to use later in the response phase.



#     def process_response(self, request, response):
#         try:
#             accessed = request.session.accessed #Checks if the session was read or written during the request.
#             modified = request.session.modified
#         except AttributeError:
#             return response

#         if not (accessed or modified):
#             return response

#         cookie_name = getattr(request, '_session_cookie_name', settings.SESSION_COOKIE_NAME)#Retrieves the session cookie name stored earlier (admin_sessionid or user_sessionid).

#         if request.session.get_expire_at_browser_close():#if session expires when browser closes, no need to set max_age or expires.
#             max_age = None
#             expires = None
#         else:
#             max_age = request.session.get_expiry_age()
#             expires_time = request.session.get_expiry_date()
#             expires = self._get_expires_time(expires_time)

#         response.set_cookie(
#             cookie_name,
#             request.session.session_key,#Writes the session cookie to the user's browser with the correct name and settings.
#             max_age=max_age,
#             expires=expires,
#             domain=settings.SESSION_COOKIE_DOMAIN,
#             path=settings.SESSION_COOKIE_PATH,
#             secure=settings.SESSION_COOKIE_SECURE or None,
#             httponly=settings.SESSION_COOKIE_HTTPONLY,
#             samesite=settings.SESSION_COOKIE_SAMESITE,
#         )
#         return response
class CustomSessionCookieMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Determine cookie name based on path
        if request.path.startswith('/admin/'):
            cookie_name = 'admin_sessionid'
        else:
            cookie_name = 'user_sessionid'  # ← Keep using this

        # Get the session engine
        engine = import_module(settings.SESSION_ENGINE)
        
        # Get session key from appropriate cookie
        session_key = request.COOKIES.get(cookie_name)
        
        # 🔥 FIX: Load the existing session properly
        request.session = engine.SessionStore(session_key)
        
        # Mark which cookie we're using
        request._session_cookie_name = cookie_name

    def process_response(self, request, response):
        try:
            accessed = request.session.accessed
            modified = request.session.modified
        except AttributeError:
            return response

        # Only save session if it was accessed or modified
        if not (accessed or modified):
            return response

        # Get the cookie name we determined in process_request
        cookie_name = getattr(request, '_session_cookie_name', settings.SESSION_COOKIE_NAME)

        # 🔥 FIX: Always save the session properly
        if modified or settings.SESSION_SAVE_EVERY_REQUEST:
            # Save session data to backend (database/cache)
            request.session.save()

        # Set cookie expiration
        if request.session.get_expire_at_browser_close():
            max_age = None
            expires = None
        else:
            max_age = request.session.get_expiry_age()
            expires_time = request.session.get_expiry_date()
            expires = self._get_expires_time(expires_time)

        # Write the session cookie
        response.set_cookie(
            cookie_name,
            request.session.session_key,
            max_age=max_age,
            expires=expires,
            domain=settings.SESSION_COOKIE_DOMAIN,
            path=settings.SESSION_COOKIE_PATH,
            secure=settings.SESSION_COOKIE_SECURE or None,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        return response

    def _get_expires_time(self, expires_time):
        return expires_time.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        # Format the time in a way that is compatible with HTTP headers
#         Situation	What Happens Next
# Session expires (user still logged in)	Django creates a new session, restores user from auth cookie
# Session flushed (e.g., logout)	Session key and auth data removed — user must log in again
# No persistent login	User becomes anonymous after session 


# for automatic deletion of expired properties according to expired date

def notify_upcoming_expiry(request=None):
    now=timezone.now()
    expiry=now + timedelta(days=30)           #minutes=2
    print("expiry")
    expiring_properties=Property.objects.filter(
        expires_at__lte=expiry,
        expires_at__gt=now,
        is_expired=False,
        reminder_sent=False
    )
    for prop in expiring_properties:
        print("prop")
        send_expiry_email(prop)
        prop.reminder_sent = True
        prop.save(update_fields=["reminder_sent"])

def send_expiry_email(property_obj):
    user=property_obj.user_profile.user
    email_subject=f"Your property '{property_obj.name}' is expiring soon."
    expiry_date = property_obj.expires_at.strftime('%Y-%m-%d %H:%M')
    print("email")

    email_body=render_to_string('property_expiry_email.html',{
        'user': user,
        'property': property_obj,
        'expiry_date': expiry_date,
        
    })

    email=EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email='krishalasth34@gmail.com',
        to=[user.email],
    )

    print("email sending")

    email.content_subtype="html"
    email.send()

def move_expired_properties_to_backup():
    expired_properties = Property.objects.filter(
        expires_at__lt=timezone.now(),
        is_expired=False    
    )       #__lt means strictly less than ->excludes items equal tot he value

    for prop in expired_properties:
        prop.is_expired=True
        prop.save(update_fields=['is_expired'])


def delete_expired_properties():
    expired_props = Property.objects.filter(backup_expires_at__lte=timezone.now())        #__lte means less than or equal->includes item equal to the value
    for prop in expired_props:
        for media in prop.media.all():
                try:
                    media.file.delete(save=False)
                except:
                    pass
                media.delete()
        prop.delete()

class CleanupExpiredPropertiesMiddleware:
    #on the basis of requests count
    """ def __init__(self, get_response):
        self.get_response = get_response
        self.runs = 0

    def __call__(self, request):
        # Run every 10 requests to reduce overhead i.e. not run on every request, reduce extra work or resource usage your application needs to perform beyond its main job.
        #if we run cleanup logic in middleware — and it executes every time someone visits or reloads a page ,
        # #we arey adding "overhead" to each request. That means: More CPU usage, More database hits (to check for expired properties), Slower response times
        self.runs += 1
        if self.runs % 2 == 0:
            delete_expired_properties()
        response = self.get_response(request)
        return response """
    
    #on the basis of time interval
    #This middleware runs every minute to delete expired properties.
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_cleanup = timezone.now() - timedelta(minutes=1)  # ensure first request triggers cleanup  # or datetime.now() - timedelta(hours=1) to start fresh
                                         

    def __call__(self, request):
        now = timezone.now()
        # Run cleanup if more than X minutes have passed since last cleanup
        if now - self.last_cleanup > timedelta(minutes=1):  # change to your desired interval, every 15 minutes or so to avoid running cleanup too frequently to reduce overhead
            
            #notify users if property will expire soon.
            notify_upcoming_expiry()
            
            # Move expired properties to backup
            move_expired_properties_to_backup()         #checks expires_at i.e. within this funct at first line i.e.(expires_at__lt=timezone.now()

            # Delete expired backups
            delete_expired_properties()                 #checks backup_rexpires_at i.e. backup_expires_at__lte=timezone.now()
            self.last_cleanup = now

        response = self.get_response(request)
        return response
# from django.shortcuts import redirect
# from django.conf import settings

# from django.contrib.sessions.middleware import SessionMiddleware
# from django.utils.deprecation import MiddlewareMixin
# from importlib import import_module


# from django.utils import timezone
# from proprietor.models import Property

# from datetime import timedelta
# import os
# from django.utils.text import slugify


# from django.core.mail import EmailMessage
# from django.template.loader import render_to_string


# # Middleware to handle authentication and guest access
# #Django stores session data on the server-side—not inside the cookie itself. The cookie only contains the session key (sessionid, user_sessionid, etc.).
# #Exactly! In Django, middleware methods like process_request() and process_response() are hooks that run before and after each view function on every HTTP request.
# #The middleware execution flow is handled deep inside Django’s core request/response handling,


# #if not logged in redirect to login page
# #Authenticated users only
# def auth(view_function):
#     def wrapped_view(request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return redirect('login')  
#         return view_function(request, *args, **kwargs)
#     return wrapped_view

# # if logged in redirect to  logout page
# # ********Guest*******
# # Guests only (unauthenticated users)
# def guest(view_function):
#     def wrapped_view(request, *args, **kwargs):
#         if request.user.is_authenticated:
#             return redirect('myprofile')  
#         return view_function(request, *args, **kwargs)
#     return wrapped_view


# #to seperate admin and user sessions so they donot collide
# class CustomSessionCookieMiddleware(MiddlewareMixin):
    
#     def process_request(self, request):
        
#         # 🔑 THE FIX: IF NOT ADMIN, EXIT IMMEDIATELY. 
#         # This allows Django's native SessionMiddleware to handle the user session.
#         if not request.path.startswith('/admin/'):
#             # Returning None lets the request continue to the next middleware (Django's SessionMiddleware)
#             return None 

#         # --- ADMIN-SPECIFIC LOGIC BELOW (Only runs if request.path.startswith('/admin/')) ---
        
#         cookie_name = 'admin_sessionid'

#         engine = import_module(settings.SESSION_ENGINE)
#         session_key = request.COOKIES.get(cookie_name)
        
#         # Manually initialize the session for the admin path
#         request.session = engine.SessionStore(session_key)
#         request._session_cookie_name = cookie_name



#     def process_response(self, request, response):
#         try:
#             accessed = request.session.accessed
#             modified = request.session.modified
#         except AttributeError:
#             return response

#         if not (accessed or modified):
#             return response

#         # Use the custom cookie name only if it was set in process_request (i.e., for admin)
#         cookie_name = getattr(request, '_session_cookie_name', None) 
        
#         # If the custom admin cookie name was set, handle the cookie writing here.
#         if cookie_name == 'admin_sessionid':
            
#             if request.session.get_expire_at_browser_close():
#                 max_age = None
#                 expires = None
#             else:
#                 max_age = request.session.get_expiry_age()
#                 expires_time = request.session.get_expiry_date()
#                 expires = self._get_expires_time(expires_time)

#             response.set_cookie(
#                 cookie_name,
#                 request.session.session_key,
#                 max_age=max_age,
#                 expires=expires,
#                 domain=settings.SESSION_COOKIE_DOMAIN,
#                 path=settings.SESSION_COOKIE_PATH,
#                 secure=settings.SESSION_COOKIE_SECURE or None,
#                 httponly=settings.SESSION_COOKIE_HTTPONLY,
#                 samesite=settings.SESSION_COOKIE_SAMESITE,
#             )
        
#         # If cookie_name is None (for non-admin paths), the native SessionMiddleware will handle 
#         # setting the default 'sessionid' cookie, which is what we want for the password reset flow.
        
#         return response

#     def _get_expires_time(self, expires_time):
#         return expires_time.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        
        
# # --- Property Cleanup Middleware and Functions (No changes needed) ---

# def notify_upcoming_expiry(request=None):
#     now=timezone.now()
#     expiry=now + timedelta(days=30)
#     print("expiry")
#     expiring_properties=Property.objects.filter(
#         expires_at__lte=expiry,
#         expires_at__gt=now,
#         is_expired=False,
#         reminder_sent=False
#     )
#     for prop in expiring_properties:
#         print("prop")
#         send_expiry_email(prop)
#         prop.reminder_sent = True
#         prop.save(update_fields=["reminder_sent"])

# def send_expiry_email(property_obj):
#     user=property_obj.user_profile.user
#     email_subject=f"Your property '{property_obj.name}' is expiring soon."
#     expiry_date = property_obj.expires_at.strftime('%Y-%m-%d %H:%M')
#     print("email")

#     email_body=render_to_string('property_expiry_email.html',{
#         'user': user,
#         'property': property_obj,
#         'expiry_date': expiry_date,
        
#     })

#     email=EmailMessage(
#         subject=email_subject,
#         body=email_body,
#         from_email='krishalasth34@gmail.com',
#         to=[user.email],
#     )

#     print("email sending")

#     email.content_subtype="html"
#     email.send()

# def move_expired_properties_to_backup():
#     expired_properties = Property.objects.filter(
#         expires_at__lt=timezone.now(),
#         is_expired=False    
#     )

#     for prop in expired_properties:
#         prop.is_expired=True
#         prop.save(update_fields=['is_expired'])


# def delete_expired_properties():
#     expired_props = Property.objects.filter(backup_expires_at__lte=timezone.now())
#     for prop in expired_props:
#         for media in prop.media.all():
#                 try:
#                     media.file.delete(save=False)
#                 except:
#                     pass
#                 media.delete()
#         prop.delete()

# class CleanupExpiredPropertiesMiddleware:
    
#     def __init__(self, get_response):
#         self.get_response = get_response
#         self.last_cleanup = timezone.now() - timedelta(minutes=1) 
                                         

#     def __call__(self, request):
#         now = timezone.now()
#         # Run cleanup if more than X minutes have passed since last cleanup
#         if now - self.last_cleanup > timedelta(minutes=1): 
            
#             #notify users if property will expire soon.
#             notify_upcoming_expiry()
            
#             # Move expired properties to backup
#             move_expired_properties_to_backup()         

#             # Delete expired backups

#             delete_expired_properties()                 
#             self.last_cleanup = now

#         response = self.get_response(request)
#         return response