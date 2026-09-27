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

NEXT_KEY = "signin_next"
EMAIL_VERIFIED = "email_verified"


def safe_next(request, raw):
    """A path on this host, or a URL on an origin in EMBED_ORIGINS (a page that
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
    return render(request, "dashboard/login.html", {
        "providers": settings.AUTH_PROVIDERS,
        "error": error,
    })


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("/")


@transaction.atomic
def person_for(userinfo):
    """The person this sign-in belongs to.

    1. Already seen: by the provider's id for them (`sub`).
    2. Else an existing account, only when the provider says the email is verified,
       exactly one account has it, and that account has no id from this provider yet.
       Anything looser lets whoever controls a matching email take over an account.
    3. Else a new account.
    """
    User = get_user_model()
    sub = str(userinfo.get("sub") or "")
    email = (userinfo.get("email") or "").strip().lower()
    if not sub:
        raise ValueError("sign-in answer has no subject")
    found = Identity.objects.select_related("user").filter(issuer=settings.OIDC_ISSUER, sub=sub).first()
    if found:
        return found.user
    user = None
    if email and userinfo.get("email_verified") is True:
        matches = list(User.objects.filter(email__iexact=email)[:2])
        if len(matches) == 1 and not matches[0].identities.filter(issuer=settings.OIDC_ISSUER).exists():
            user = matches[0]
    if user is None:
        user = User.objects.create_user(
            username=free_username(User, email or f"{sub}@{urlsplit(settings.OIDC_ISSUER).netloc}"),
            email=email,
            first_name=(userinfo.get("name") or "")[:150],
        )
        user.set_unusable_password()
        user.save()
    Identity.objects.create(user=user, issuer=settings.OIDC_ISSUER, sub=sub)
    return user


def free_username(User, wanted):
    name, n = wanted[:150], 1
    while User.objects.filter(username=name).exists():
        n += 1
        suffix = f"-{n}"
        name = wanted[:150 - len(suffix)] + suffix
    return name


class Callback(lt.CallbackView):
    """The provider sends the person back here. Sign them in to this host and send
    them where they were going."""

    def get_or_create_user(self, userinfo):
        self._person = person_for(userinfo)
        self._email_verified = userinfo.get("email_verified") is True
        return self._person, {}

    def _success(self, request, tokens):
        login(request, self._person, backend="django.contrib.auth.backends.ModelBackend")
        # VolKit: "My articles" matches Ghost authors by email, so only a verified one.
        request.session[EMAIL_VERIFIED] = self._email_verified
        return redirect(safe_next(request, request.session.pop(NEXT_KEY, "/")))

    def _fail(self, request, error_code):
        return redirect(f"/auth/login/?error={error_code}")
