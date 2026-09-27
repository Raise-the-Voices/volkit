from django import template
from django.utils.html import format_html, format_html_join

register = template.Library()


@register.simple_tag(takes_context=True)
def element_card(context, card, org):
    """A custom element card. data-up is the peer's API, or this frame for its own
    cards; `attrs` from the dashboard file add to or override it. The tag and
    attribute names were checked against patterns in the view."""
    request = context["request"]
    attrs = {"data-org": org.slug}
    if card.get("peer"):
        attrs.update({"data-up": card["peer"].api_url, "data-app": card["peer"].app_url})
    elif card.get("own"):
        attrs["data-up"] = f"{request.scheme}://{request.get_host()}"
    attrs.update(card.get("attrs", {}))
    return format_html(
        "<{0}{1}></{0}>", card["tag"],
        format_html_join("", ' {}="{}"', sorted(attrs.items())),
    )
