from rest_framework import permissions


class IsAdminAuthorOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    message = 'Access denied'

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )
