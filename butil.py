from datetime import datetime, timedelta
import pytz

def now_epoch():

    now = datetime.utcnow()
    epoch = datetime.utcfromtimestamp(0)
    since = (now - epoch).total_seconds()

    return int(since)


def pretty_until(utc_dt):
    """ Takes a non-naive UTC datetime, comparing against the current time """

    diff = utc_dt - pytz.utc.localize(datetime.utcnow())
    secs = int(diff.seconds)
    days = int(diff.days)

    entities = []

    if days >= 1:
        temp = '{} day{s}'.format(
            days,
            s='s' if days > 1 else '')

        entities.append(temp)

    if secs > 3600:
        hours = secs // 3600
        temp = '{} hour{s}'.format(
            hours,
            s='s' if hours > 1 else '')

        entities.append(temp)

        secs -= (hours * 3600)

    if secs > 60:
        mins = secs // 60
        temp = '{} minute{s}'.format(
            mins,
            s='s' if mins > 1 else '')

        entities.append(temp)

    until_msg = ', '.join(entities)

    return until_msg


def pretty_since(dt):
    """ Takes a naive UTC datetime, comparing against the current time """

    diff = datetime.utcnow() - dt
    secs = int(diff.seconds)
    days = int(diff.days)

    since_msg = ''

    if days > 0:
        since_msg += '{d} day{s}'.format(
            d=days,
            s='s' if days > 1 else '')
    else:
        hours = secs // 3600
        if hours > 0:
            since_msg += '{h} hour{s}'.format(
                h=hours,
                s='s' if hours > 1 else '')
        else:
            minutes = secs // 60
            since_msg += '{m} minute{s}'.format(
                m=minutes,
                s='s' if minutes > 1 else '')
    
    return since_msg


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = int(diff.seconds)
    day_diff = int(diff.days)

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return "%d seconds ago" % second_diff
        if second_diff < 120:
            return "1 minute ago"
        if second_diff < 3600:
            return "%d minutes ago" % (second_diff / 60)
        if second_diff < 7200:
            return "1 hour ago"
        if second_diff < 86400:
            return "%d hours ago" % (second_diff / 3600)
    if day_diff == 1:
        return "1 day ago"
    if day_diff < 7:
        return "%d days ago" % (day_diff)
    if day_diff < 14:
        return "1 week ago"
    if day_diff < 31:
        return "%d weeks ago" % (day_diff / 7)
    if day_diff < 62:
        return "1 month ago"
    if day_diff < 365:
        return "%d months ago" % (day_diff / 30)
    if day_diff < 730:
        return "1 year ago"
    return "%d years ago" % (day_diff / 365)


def pretty_seconds(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if h > 0:
        return '{}h {}m {}s'.format(h, m, s)
    else:
        return '{}m {}s'.format(m, s)
