from django import template

register = template.Library()


@register.filter
def sum_attribute(sequence, attribute):
    if not sequence:
        return 0
    return sum(item.get(attribute, 0) for item in sequence)
