import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import Group
from ldap3 import ALL, SUBTREE, Connection, Server

logger = logging.getLogger("security")


class LDAPBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not settings.LDAP_ENABLED or not username or not password:
            return None
        try:
            server = Server(settings.LDAP_SERVER_URI, use_ssl=settings.LDAP_USE_SSL, get_info=ALL)
            bind_user = settings.LDAP_BIND_DN or f"{settings.LDAP_USER_DOMAIN}\\{username}"
            bind_password = settings.LDAP_BIND_PASSWORD or password
            with Connection(server, user=bind_user, password=bind_password, auto_bind=True) as conn:
                query = settings.LDAP_USER_FILTER.format(username=username)
                if settings.LDAP_BIND_DN:
                    conn.search(
                        settings.LDAP_BASE_DN,
                        query,
                        search_scope=SUBTREE,
                        attributes=["mail", "givenName", "sn", "memberOf", "userPrincipalName"],
                    )
                    if not conn.entries:
                        return None
                    entry = conn.entries[0]
                    with Connection(server, user=entry.entry_dn, password=password, auto_bind=True):
                        pass
                else:
                    conn.search(
                        settings.LDAP_BASE_DN,
                        query,
                        search_scope=SUBTREE,
                        attributes=["mail", "givenName", "sn", "memberOf"],
                    )
                    entry = conn.entries[0] if conn.entries else None
                User = get_user_model()
                user, _ = User.objects.get_or_create(
                    username=username, defaults={"account_type": "LDAP"}
                )
                user.account_type = "LDAP"
                user.email = str(entry.mail) if entry and "mail" in entry else user.email
                user.first_name = (
                    str(entry.givenName) if entry and "givenName" in entry else user.first_name
                )
                user.last_name = str(entry.sn) if entry and "sn" in entry else user.last_name
                user.is_active = True
                user.set_unusable_password()
                user.save()
                memberships = {
                    str(v).lower()
                    for v in (entry.memberOf.values if entry and "memberOf" in entry else [])
                }
                role_map = {
                    settings.LDAP_ADMIN_GROUP: "License Administrators",
                    settings.LDAP_MANAGER_GROUP: "License Managers",
                    settings.LDAP_READER_GROUP: "License Readers",
                }
                user.groups.remove(*Group.objects.filter(name__in=role_map.values()))
                for ad_group, local_group in role_map.items():
                    if ad_group and any(ad_group.lower() in value for value in memberships):
                        user.groups.add(Group.objects.get(name=local_group))
                return user
        except Exception as exc:
            logger.warning(
                "LDAP authentication failed for user %s: %s", username, type(exc).__name__
            )
            return None

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None
