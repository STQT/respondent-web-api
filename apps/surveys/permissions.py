from rest_framework import permissions


class IsModeratorPermission(permissions.BasePermission):
    """
    Permission that allows access only to moderators.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_moderator
        )


class IsSuperUserOrModeratorPermission(permissions.BasePermission):
    """
    Permission that allows access to superusers and moderators.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_superuser or request.user.is_moderator)
        )
