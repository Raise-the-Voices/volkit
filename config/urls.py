from django.contrib import admin
from django.urls import include, path

from linkedtrust_auth.views import RedirectView

from frame import api, auth, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/login/", auth.login_page, name="login"),
    path("auth/logout/", auth.logout_view, name="logout"),
    path("auth/linkedtrust/redirect", RedirectView.as_view(), name="linkedtrust_start"),
    path("auth/linkedtrust/callback", auth.Callback.as_view(), name="linkedtrust_callback"),
    path("api/", include(api.urls)),
    path("", views.home, name="home"),
    path("o/<slug:org>/", views.dashboard, name="dashboard"),
    path("o/<slug:org>/<slug:dashboard>/", views.dashboard, name="dashboard_named"),
]
