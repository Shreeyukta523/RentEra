$(document).on('click', '.updatefav', function(e) {
    e.preventDefault();

    var property_id = $(this).closest('.property_data').find('.prop_id').val();
    var token = $('input[name=csrfmiddlewaretoken]').first().val();
    var icon = $(this).children('i');

    $.ajax({
        type: "POST",
        url: "/updatefavourite/",
        data: {
            'property_id': property_id,
            csrfmiddlewaretoken: token
        },
        success: function(response) {
            if (response.status === 'added') {
                icon.removeClass('fa-heart-o').addClass('fa-heart');
                icon.css('color', 'red');
            } else if (response.status === 'removed') {
                icon.removeClass('fa-heart').addClass('fa-heart-o');
                icon.css('color', '');
            }
        },
        error: function(err) {
            console.log('Error updating favourite:', err);
        }
    });
}); // ✅ click handler closed

$('.property_data').each(function() {
    var property_id = $(this).find('.prop_id').val();
    var icon = $(this).find('.updatefav i');

    $.ajax({
        type: "GET",
        url: "/checkfavourite/",
        data: {'property_id': property_id},
        success: function(response) {
            if (response.in_fav) {
                icon.removeClass('fa-heart-o').addClass('fa-heart');
                icon.css('color', 'red');
            }
        },
        error: function(err) {
            console.log('Error checking favourite:', err);
        }
    });
}); 


$(document).on('click', '.delete-favourite', function(e) {
    e.preventDefault();
    e.stopPropagation();

    var property_id = $(this).data('id');     // <-- get ID instead of slug
    var token = $('input[name=csrfmiddlewaretoken]').val();

    $.ajax({
        type: "POST",
        url: "/deletefav/",  
        data: {
            'property_id': property_id,       // <-- send ID
            csrfmiddlewaretoken: token
        },
        success: function(response) {
            console.log(response);
            sessionStorage.setItem('notificationType', 'success');
            sessionStorage.setItem('notificationMessage', 'Removed from favourites');
            location.reload();
        },
        error: function(err) {
            console.log('Error deleting favourite:', err);
        }
    });
});
