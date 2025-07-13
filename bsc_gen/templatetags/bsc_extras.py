from django import template

register = template.Library()

@register.filter
def floatval(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0 

@register.filter
def dict_get(d, key):
    try:
        return d.get(key)
    except Exception:
        return None 