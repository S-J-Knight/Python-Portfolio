"""
Custom middleware to set Permissions-Policy header for admin canvas operations
"""

class PermissionsPolicyMiddleware:
    """
    Middleware to set Permissions-Policy header allowing canvas operations in admin
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only apply to admin pages to keep other pages secure
        if request.path.startswith('/admin/'):
            # Allow unload events for canvas.toDataURL()
            # Use * to allow for all origins in admin
            response['Permissions-Policy'] = 'unload=*'
        
        return response
