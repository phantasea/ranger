# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

from datetime import datetime

from ranger.core.shared import SettingsAware

# add by sim1
def size_fmt(bytes, separator=''):
    """
    xxxxxxxx --> xxx.x[BKMGTPEZ]
    """
    base = 1024.0
    if not SettingsAware.settings.binary_size_prefix:
        base = 1000.0

    if bytes <= 0:
        return '     0'

    for unit in ["B", "K", "M", "G", "T", "P"]:
        if bytes < base:
            val = f"{bytes:5.1f}"
            if len(val) < 5:
                val = f"{float(val): 5.1f}"
            return val + separator + unit
        bytes /= base

    return "TooBig"


def human_readable(byte, separator=' ', use_opt=False, uni_format=False):  # pylint: disable=too-many-return-statements
    """Convert a large number of bytes to an easily readable format.
    """

    # add by sim1
    if use_opt:
        if SettingsAware.settings.size_separator_space:
            separator = ' '
        else:
            separator = ''

    # handle automatically_count_files false
    if byte is None:
        return ''
    if byte <= 0:
        return '0'
    if SettingsAware.settings.size_in_bytes:
        return format(byte, 'n')  # 'n' = locale-aware separator.

    # I know this can be written much shorter, but this long version
    # performs much better than what I had before.  If you attempt to
    # shorten this code, take performance into consideration.

    # mod by sim1
    if uni_format:
        return size_fmt(byte, separator)

    if byte <= 0:
        return '0'
    elif byte < 2**10:
        return '%d.0%sB' % (byte, separator)
    elif byte < 2**20:
        return '%.1f%sK' % ((byte / 2**10), separator)
    elif byte < 2**30:
        return '%.1f%sM' % ((byte / 2**20), separator)
    elif byte < 2**40:
        return '%.1f%sG' % ((byte / 2**30), separator)
    elif byte < 2**50:
        return '%.1f%sT' % ((byte / 2**40), separator)
    elif byte < 2**60:
        return '%.1f%sP' % ((byte / 2**50), separator)
    else:
        return 'TooBig'


def human_readable_time(timestamp):
    """Convert a timestamp to an easily readable format.
    """
    # Hard to test because it's relative to ``now()``
    try:
        date = datetime.fromtimestamp(timestamp)
    except ValueError:
        return '???'

    datediff = datetime.now().date() - date.date()
    if datediff.days >= 365:
        return date.strftime("%-d %b %Y")
    elif datediff.days >= 7:
        return date.strftime("%-d %b")
    elif datediff.days >= 1:
        return date.strftime("%a")
    return date.strftime("%H:%M")


if __name__ == '__main__':

    # XXX: This mock class is a temporary (as of 2019-01-27) hack.
    class SettingsAwareMock(object):  # pylint: disable=too-few-public-methods
        class settings(object):  # pylint: disable=invalid-name,too-few-public-methods
            size_in_bytes = False
            binary_size_prefix = True
    SettingsAware = SettingsAwareMock  # noqa: F811

    import doctest
    import sys
    sys.exit(doctest.testmod()[0])
