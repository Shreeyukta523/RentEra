from functools import wraps
from django.shortcuts import redirect


#role based decorators i.e. to direct users to specific vies based on their role
def proprietor(view_func):      
    @wraps(view_func)           #here for example user visits add_property(request), then django calls add_property(request) function but it is decorated ie.e @proprietor is used so it instead calls wrapper(request) and inside of it is checked
    def wrapper(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.role == 'proprietor' :
            return view_func(request, *args, **kwargs )
        return redirect('home')                         #in case not proprietor
    return wrapper


def renter(view_func):
    @wraps(view_func)                       #@wraps(view_func) is a decorator which ensures wrapper function retains name, docstring and metadata or original view function
    def wrapper(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.role == 'renter':
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return wrapper



#decorator is a function that takes another functoion ad input, add extra logic and returns new function that can do more than original one
#i.e. takes original view function as input, and the wrapper adds something. for eg: here to check acess for proprietor and renter