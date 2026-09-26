from django.contrib import admin

from .models import DashLayout, Identity, Membership, NavPlace, Org, Peer


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Org)
class OrgAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


@admin.register(Peer)
class PeerAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "app_url", "api_url", "embed_url")


@admin.register(NavPlace)
class NavPlaceAdmin(admin.ModelAdmin):
    list_display = ("label", "url", "roles", "order")
    list_editable = ("order",)


admin.site.register(Identity)
admin.site.register(DashLayout)
