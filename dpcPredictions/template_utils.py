from datetime import datetime


def format_time(value, format='%Y-%m-%d %H:%M'):
    """Format  date time to: d Mon YYYY HH:MM P"""
    if value is None:
        return ''
    else:
        date = datetime.strptime(value, format)
        return '{}.{}.{}'.format(date.day, date.strftime('%b'), date.year)
