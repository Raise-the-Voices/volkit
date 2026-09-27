from django.contrib import admin

from .models import App, DashLayout, Identity, NavPlace


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "app_url", "api_url", "embed_url")


@admin.register(NavPlace)
class NavPlaceAdmin(admin.ModelAdmin):
    list_display = ("label", "url", "order")
    list_editable = ("order",)


admin.site.register(Identity)
admin.site.register(DashLayout)
