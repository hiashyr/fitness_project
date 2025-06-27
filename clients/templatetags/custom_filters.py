from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получение значения из словаря по ключу в шаблоне"""
    return dictionary.get(key)

@register.filter
def duration_format(seconds):
    """Форматирование секунд в ЧЧ:ММ"""
    if not seconds:
        return ""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}"