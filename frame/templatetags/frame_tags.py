from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def peer_card(card, org):
    """A peer's custom element. The tag name was checked against a pattern in the view."""
    return format_html(
        '<{0} data-up="{1}" data-org="{2}" data-app="{3}"></{0}>',
        card["tag"], card["peer"].api_url, org.slug, card["peer"].app_url,
    )
