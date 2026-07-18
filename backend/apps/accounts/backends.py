from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.utils import timezone


class LockoutBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        if user.locked_until and user.locked_until > timezone.now():
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_attempts", "locked_until"])
            return user
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            user.locked_until = timezone.now() + timedelta(seconds=settings.LOGIN_LOCKOUT_SECONDS)
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        return None
