"""Sign-in: OIDC against OIDC_ISSUER (LinkedTrust by default), ending in a Django
session on this host. The provider keeps its own session, so a person already
signed in anywhere else passes straight through (CONTRACT.md section 1)."""

from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from linkedtrust_auth import views as lt

from .models import Identity

NEXT_KEY = "baobab_next"


def safe_next(request, raw):
    """A path on this host, or a URL on an origin in EMBED_ORIGINS (a frond that
    sent the person here to sign in). Anything else goes home."""
    if not raw:
        return "/"
    if url_has_allowed_host_and_scheme(raw, allowed_hosts={request.get_host()},
                                       require_https=request.is_secure()):
        return raw
    parts = urlsplit(raw)
    if f"{parts.scheme}://{parts.netloc}" in settings.EMBED_ORIGINS:
        return raw
    return "/"


def login_page(request):
    nxt = safe_next(request, request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(nxt)
    request.session[NEXT_KEY] = nxt
    error = request.GET.get("error", "")
    if settings.AUTH_PROVIDERS == ["linkedtrust"] and not error:
        return redirect("linkedtrust_start")
    return render(request, "frame/login.html", {
        "providers": settings.AUTH_PROVIDERS,
        "error": error,
    })


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("/")


@transaction.atomic
def person_for(userinfo):
    """The person this sign-in belongs to: by provider id, else by the verified
    email (then remembered by id), else a new account."""
    User = get_user_model()
    sub = str(userinfo.get("sub") or "")
    email = (userinfo.get("email") or "").strip().lower()
    if not sub:
        raise ValueError("sign-in answer has no subject")
    found = Identity.objects.select_related("user").filter(issuer=settings.OIDC_ISSUER, sub=sub).first()
    if found:
        return found.user
    user = User.objects.filter(email__iexact=email).first() if email else None
    if user is None:
        user = User.objects.create_user(
            username=email or f"{sub}@{urlsplit(settings.OIDC_ISSUER).netloc}",
            email=email,
            first_name=(userinfo.get("name") or "")[:150],
        )
        user.set_unusable_password()
        user.save()
    Identity.objects.create(user=user, issuer=settings.OIDC_ISSUER, sub=sub)
    return user


class Callback(lt.CallbackView):
    """The provider sends the person back here. Sign them in to this host and send
    them where they were going."""

    def get_or_create_user(self, userinfo):
        self._person = person_for(userinfo)
        return self._person, {}

    def _success(self, request, tokens):
        login(request, self._person, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(safe_next(request, request.session.pop(NEXT_KEY, "/")))

    def _fail(self, request, error_code):
        return redirect(f"/auth/login/?error={error_code}")
