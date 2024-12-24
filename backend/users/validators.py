from django.core.exceptions import ValidationError

from foodgram import constants as c


def validate_username_not_me(value):
    if value == c.VALIDATE_USERNAME:
        raise ValidationError(f'Username {c.VALIDATE_USERNAME}'
                              'is not allowed.')
