from django.contrib import admin
from .models import Property, Facility
from .models import Land_number
from django.utils.html import format_html
from django.utils.safestring import mark_safe


# Inline facilities editor for Property (ManyToManyField)
class FacilityInline(admin.TabularInline):
    model = Property.facilities.through
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ( 
        'name',
        'District',
        'Municipality',
        'province',
        'ward_no',
        'property_type',
        'price',
        'number_of_rooms',
        'is_verified',
        'sheet_no',
        'thumbnail_preview'
    )
    list_filter = ('province', 'property_type', 'District', 'Municipality', 'sheet_no')
    search_fields = ('name', 'address', 'District', 'Municipality', 'sheet_no', 'land_no')
    
    def thumbnail_preview(self, obj):
        """Show multiple thumbnails (images + videos) for each property"""
        media_html = ""
        for media in obj.media.all()[:4]:  # show up to 4 previews
            if media.media_type == 'image':
                media_html += f'''
                    <img src="{media.file.url}" 
                        style="height:60px; width:60px; object-fit:cover; margin:2px; border-radius:6px;" />
                '''
            elif media.media_type == 'video':
                media_html += f'''
                    <video style="height:60px; width:60px; object-fit:cover; margin:2px; border-radius:6px;" controls>
                        <source src="{media.file.url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                '''
        if not media_html:
            media_html = "<span style='color:gray;'>No media</span>"
        return mark_safe(media_html)

    thumbnail_preview.short_description = "Media Preview"
    #exclude = ('facilities',)  # hide the automatic M2M widget

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)




@admin.register(Land_number)
class LandNumberAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'citizenship_number',
        'province',
        'District',
        'Municipality',
        'ward_no',
        'land_no',
        'sheet_no'
        
    )
    search_fields = (
        'first_name', 'last_name',
        'citizenship_number',
        'District', 'Municipality',
        'land_no', 'sheet_no'
    )
    list_filter = ('province', 'District', 'ward_no', 'created_at')
    ordering = ('last_name', 'first_name')

    readonly_fields = ('created_at', 'updated_at')

