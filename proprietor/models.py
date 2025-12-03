# proprietor/models.py

from django.db import models
from django.contrib.auth.models import User
from rentals.models import UserProfile # This import is fine
from django.utils.text import slugify

from django.utils import timezone
from datetime import timedelta                      #for time in minutes ,days..
from dateutil.relativedelta import relativedelta        #for months
import magic
from PIL import Image
from django.core.exceptions import ValidationError

class Facility(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name   
    
PROPERTY_TYPES = [
    ('room', 'Room'),
    ('house', 'House'),
    ('flat and apartment', 'Flat and Apartment'),
    ('office space', 'Office Space'),
    ('shutters and shops', 'Shutters and Shops'),
]

PROVINCES = [
    ('1', 'Province No. 1 (Koshi)'),
    ('2', 'Province No. 2 (Madhesh)'),
    ('3', 'Province No. 3 (Bagmati)'),
    ('4', 'Province No. 4 (Gandaki)'),
    ('5', 'Province No. 5 (Lumbini)'),
    ('6', 'Province No. 6 (Karnali)'),
    ('7', 'Province No. 7 (Sudurpashchim)'),
]

def validate_media_file(file):
    file_mime = magic.from_buffer(file.read(2048), mime=True)  #Reads the first 2KB of the file and checks the actual binary content.
    file.seek(0)  # Reset pointer after reading

    max_image_size = 10 * 1024 * 1024
    max_video_size = 50 * 1024 *1024

    if file_mime.startswith('image'):
        try:
            img = Image.open(file)
            img.verify()
        except Exception:
            raise ValidationError("Invalid or corrupted image file.")
        finally:
            file.seek(0)
        
        if file.size > max_image_size:
            raise ValidationError("Image file too large (max 5MB).")
        

    elif file_mime.startswith('video'):
        if file.size > max_video_size:
            raise ValidationError("Video file too large(max 50MB).")
    
    else:
        raise ValidationError("Unsupported file type.Only images and videos are allowed.")
    

class Property(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)

    slug = models.SlugField(unique=True, blank=True, null=True)
    name = models.CharField(max_length=200)
    province = models.CharField(max_length=30, choices=PROVINCES)
    address = models.CharField(max_length=300)
    Municipality = models.CharField(max_length=300 ,blank=True, null=True)
    District = models.CharField(max_length=100)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    ward_no = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPES)
    number_of_rooms = models.PositiveIntegerField()
    description = models.TextField()
    facilities = models.ManyToManyField(Facility)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    sheet_no=models.PositiveIntegerField(blank=True, null=True)
    land_no=models.PositiveIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    backup_expires_at=models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    is_expired=models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):

        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=4) # we could have done self.created_at + timedelta(days=30)  but  we are saving the property only later after payment so we are using timezone.now() as the base time
            #self.expires_at = timezone.now()  + timedelta(days=30)  # expire after 30 days 
            #self.expires_at = timezone.now() + relativedelta(months=6)        # expire after 6 months
            self.backup_expires_at = self.expires_at +timedelta(minutes=2)     #days=30 later

        # generates slug if slug is not provided
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            num = 1
            while Property.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{num}"
                num += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def main_image(self):
        media = self.media.filter(media_type='image').first()
        if media:
            return media.file.url
        return None

def property_media_upload_path(instance,filename):
     # Upload images and videos to separate folders according to its property id
    mime = magic.from_buffer(instance.file.read(2048), mime=True)
    instance.file.seek(0)
    if mime.startswith('video'):
        return f'properties/videos/{instance.property.id}/{filename}'
    return f'properties/images/{instance.property.id}/{filename}'

class PropertyMedia(models.Model):
    MEDIA_CHOICES = [('image', 'Image'), ('video', 'Video')]
    property = models.ForeignKey('Property',on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to=property_media_upload_path, validators=[validate_media_file])
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        mime = magic.from_buffer(self.file.read(2048), mime=True)
        self.file.seek(0)
        if mime.startswith('image'):
            self.media_type = 'image'
        elif mime.startswith('video'):
            self.media_type = 'video'
        else:
            raise ValidationError("Unsupported file type.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.media_type.capitalize()} - {self.property.name}"

class Land_number(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    # Citizenship Number field with specific length for the format XX-XX-XX-XXXXX
    # Added unique=True if each citizenship number must be distinct in this list
    citizenship_number = models.CharField(max_length=14)
    land_no= models.PositiveIntegerField(blank=True, null=True) 
    sheet_no=models.PositiveIntegerField(blank=True, null=True)
    province = models.CharField(max_length=30, choices=PROVINCES)
    Municipality = models.CharField(max_length=300 ,blank=True, null=True)
    District = models.CharField(max_length=100)
    ward_no = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rental House land Record"
        verbose_name_plural = "Land Records"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.District}{self.Municipality}({self.land_no})"
 
