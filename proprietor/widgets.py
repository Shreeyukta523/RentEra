# proprietor/widgets.py

from django import forms
from django.utils.safestring import mark_safe

class LeafletSearchMapWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        # `name` will be 'latitude'
        # `value` will be the current latitude value from the model instance (if editing) or None
        # `attrs` contains attributes like {'id': 'id_latitude'} passed from Django's form rendering

        # Get the actual ID Django expects for the field's input element
        field_input_id = attrs.get('id', f'id_{name}') # e.g., 'id_latitude'

        # Generate unique IDs for the search input and map container
        search_input_id = f'search_{name}_input'      # e.g., 'search_latitude_input'
        map_container_id = f'map_{name}_container'    # e.g., 'map_latitude_container'

        # The HTML we're returning should now include:
        # 1. The actual input field for 'latitude' (which JS will update)
        # 2. The search input for the geocoder
        # 3. The div for the map itself

        html = f"""
            <input type="text"
                   name="{name}"
                   id="{field_input_id}"
                   value="{value if value is not None else ''}"
                   class="form-control leaflet-coordinate-display"
                   readonly
                   placeholder="Latitude"
                   style="width: 100%; padding: 6px; margin-bottom: 5px; font-weight: bold;"
            />
            
            <input type="text" id="{search_input_id}" class="form-control leaflet-search-input"
                   placeholder="Search city or street..."
                   style="width: 100%; padding: 6px; margin-bottom: 5px;"
            />
            
            <div id="{map_container_id}" style="height: 400px; width: 100%;"></div>
        """
      
        html = f"""
            <input type="hidden"
                   name="{name}"
                   id="{field_input_id}"
                   value="{value if value is not None else ''}"
                   class="form-control leaflet-coordinate-display"
                   readonly
                   placeholder="Latitude"
                   style="width: 100%; padding: 6px; margin-bottom: 5px; font-weight: bold;"
            />
            
            <input type="text" id="{search_input_id}" class="form-control leaflet-search-input"
                   placeholder="Search city or street..."
                   style="width: 100%; padding: 6px; margin-bottom: 5px;"
            />
            
            <div id="{map_container_id}" style="height: 400px; width: 100%;"></div>
        """
        return mark_safe(html)