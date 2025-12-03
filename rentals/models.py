# rentals/models.py

from django.db import models
from django.contrib.auth.models import User
import uuid
# No longer importing Property from proprietor.models directly here to avoid circular dependency
# from proprietor.models import Property # REMOVE THIS LINE

class BaseModel(models.Model):
    uid = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True) # Changed from auto_now=True
    updated_at = models.DateTimeField(auto_now=True) # Changed from auto_now_add=True

    class Meta:
        abstract = True


class ListOfCitizenship(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    citizenship_number = models.CharField(max_length=14, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Citizenship Record"
        verbose_name_plural = "Citizenship Records"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.citizenship_number})"


class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    phone_number = models.CharField(max_length=10)
    citizenship_number = models.CharField(max_length=14, blank=True, null=True)
    ROLE_CHOICES = (
        ('proprietor', 'Proprietor'),
        ('renter', 'Renter'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    is_verified = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='profile', blank=True, null=True)
    citizenship_image = models.ImageField(upload_to='profile', blank=True, null=True)
    address = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.role.capitalize()}"


# NEW MODELS: Request, Conversation, Message
class Request(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    renter = models.ForeignKey('rentals.UserProfile', on_delete=models.CASCADE, related_name='sent_requests', limit_choices_to={'role': 'renter'})
    proprietor = models.ForeignKey('rentals.UserProfile', on_delete=models.CASCADE, related_name='received_requests', limit_choices_to={'role': 'proprietor'})
    property = models.ForeignKey('proprietor.Property', on_delete=models.CASCADE, related_name='requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # IMPORTANT: No unique_together here. Uniqueness for 'pending' requests is handled in the view.
        ordering = ['-created_at'] # Order by newest first

    def __str__(self):
        return f"Request from {self.renter.user.username} to {self.proprietor.user.username} for {self.property.name} ({self.status})"

class Message(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)  # link to accepted request
    sender = models.ForeignKey(User, on_delete=models.CASCADE)      #eithere proprietor or renter the one who send
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


# class Conversation(models.Model):
#     request = models.OneToOneField(Request, on_delete=models.CASCADE, related_name='conversation')
#     participants = models.ManyToManyField(User, related_name='conversations')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Conversation for Request {self.request.id} - {self.request.property.name}"


# class Message(models.Model):
#     conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
#     sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
#     content = models.TextField()
#     timestamp = models.DateTimeField(auto_now_add=True)
#     is_read = models.BooleanField(default=False)

#     class Meta:
#         ordering = ['timestamp']

#     def __str__(self):
#         return f"Message from {self.sender.username} in Conversation {self.conversation.id}"


from django.db import models
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
import random

# Get the custom or default User model
User = get_user_model()

class PasswordResetOTP(models.Model):
    """
    Stores the One-Time Password for password reset functionality.
    """
    # Use OneToOneField to ensure only one active OTP per user
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Set expiration for 5 minutes (adjust as needed)
    expires_at = models.DateTimeField() 

    def save(self, *args, **kwargs):
        # Initialize expires_at on creation if not set
        if not self.id:#Checks if the object is being saved for the very first time (self.id will be None).
             self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)#Calls the original models.Model save method to actually persist the data (including expires_at) to the database.

    def is_valid(self):
        """Checks if the OTP is still within its expiration window."""
        return timezone.now() < self.expires_at

    def generate_otp(self):#Defines a method to create a new random code and reset its validity period.
        """Generates a new 6-digit code and resets the expiration timer."""
        # Generate a 6-digit random number
        self.otp_code = str(random.randint(100000, 999999))
        self.expires_at = timezone.now() + timedelta(minutes=5)
        self.save()
        
    def __str__(self):
        return f"OTP for {self.user.username}"