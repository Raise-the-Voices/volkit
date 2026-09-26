from django.conf import settings


def volkit(request):
    """VolKit's addresses, for its own card templates."""
    return {"volkit_cases_url": settings.VOLKIT_CASES_URL}
