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

@register.filter
def duration_hm(minutes):
    """Форматирование минут в строку 'X ч. Y мин.'"""
    if not minutes:
        return "0 мин."
    try:
        minutes = int(round(float(minutes)))
    except (TypeError, ValueError):
        return "-"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours} ч. {mins} мин."
    return f"{mins} мин."