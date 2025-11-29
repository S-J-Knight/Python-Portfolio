from django import template
register = template.Library()

@register.filter
def dict_get(d, key):
    return d.get(key, 0)

@register.filter
def points_to_pounds(points):
    """Convert points to pounds (100 points = £1.00)"""
    if not points:
        return "0.00"
    return f"{points / 100:.2f}"
