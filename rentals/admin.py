from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, Message
from .models import ListOfCitizenship ,Request

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
    'get_username', 'get_first_name', 'get_last_name',
    'phone_number', 'role', 'is_verified','citizenship_number',
    'profile_image_tag', 'citizenship_image_tag',)
    def get_username(self, obj):
        return obj.user.username
    get_username.admin_order_field = 'user__username'  # allows column sorting
    get_username.short_description = 'Username'       # column header

    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.admin_order_field = 'user__first_name'
    get_first_name.short_description = 'First Name'

    def get_last_name(self, obj):
        return obj.user.last_name
    get_last_name.admin_order_field = 'user__last_name'
    get_last_name.short_description = 'Last Name'
    search_fields = ('user__username', 'phone_number', 'role')
    list_filter = ('role', 'is_verified')

    def profile_image_tag(self, obj):
        if obj.profile_image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.profile_image.url)
        return "-"
    profile_image_tag.short_description = 'Profile Image'

    def citizenship_image_tag(self, obj):
        if obj.citizenship_image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.citizenship_image.url)
        return "-"
    citizenship_image_tag.short_description = 'Citizenship Image'

@admin.register(ListOfCitizenship)
class ListOfCitizenshipAdmin(admin.ModelAdmin):
    # Fields to display in the list view of the admin panel
    list_display = (
        'first_name',
        'last_name',
        'citizenship_number',
        'created_at', # If you added these fields in your model
        'updated_at', # If you added these fields in your model
    )
    
    # Fields to allow searching by
    search_fields = (
        'first_name',
        'last_name',
        'citizenship_number',
    )
    
    # Fields to allow filtering by (if applicable, e.g., for status or date ranges)
    # list_filter = ('created_at',) # Example: Filter by creation date
    
    # Fields to make clickable links to the detail view
    list_display_links = ('citizenship_number', 'first_name', 'last_name')
    
    # Fields to make editable directly from the list view (use with caution)
    # list_editable = ('citizenship_number',) # Example: allows editing directly in list

    # Fieldset for grouping fields in the add/change form (optional)
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'citizenship_number')
        }),
        ('Timestamps', { # This fieldset is only if you added created_at/updated_at
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',), # Makes it collapsible
        }),
    )#2grops in admin while adding
    # Make created_at and updated_at read-only
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Request) # Decorator alternative to admin.site.register()
class RequestAdmin(admin.ModelAdmin):
    list_display = ('renter', 'proprietor', 'property', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'property__property_type') # Filter by status, creation date, and property type
    search_fields = ('renter__user__username', 'proprietor__user__username', 'property__name') # Search by usernames and property name
    raw_id_fields = ('renter', 'proprietor', 'property') # Use raw ID input for FKs for large datasets
    readonly_fields = ('created_at', 'updated_at') # Make these fields read-only
    # You can also define custom actions, fieldsets, etc.

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    # This specifies the fields to display in the list view of the admin panel.
    list_display = ('request', 'sender', 'text', 'timestamp')

    # This adds a filter sidebar to filter messages by their timestamp.
    list_filter = ('timestamp',)

    # This adds a search bar that can search for messages by text or sender's username.
    search_fields = ('text', 'sender__username')

    # This makes the timestamp field read-only in the detailed message view.
    readonly_fields = ('timestamp',)
