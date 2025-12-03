from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from proprietor.models import Property

#to ceate text-based and part behavior-based recommendation system i.e. hybrid

class UserActivity(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    property=models.ForeignKey(Property, on_delete=models.CASCADE)
    activity_type=models.CharField(
        max_length=50, 
        choices=[
            ('view', 'View'),
            ('click', 'Click'),
            ('search','Search'),
            ('filter', 'Filter')
        ]
    )
    timestamp=models.DateTimeField(default=timezone.now)
    meta_info=models.JSONField(blank=True, null=True)  # optional details (like filters used)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.property.name}"

