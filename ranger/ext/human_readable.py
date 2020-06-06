# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

from datetime import datetime

from ranger.core.shared import SettingsAware


def human_readable(byte, separator=' '):  # pylint: disable=too-many-return-statements
    """Convert a large number of bytes to an easily readable format.

    >>> human_readable(54)
    '54 B'
    >>> human_readable(1500)
    '1.46 K'
    >>> human_readable(2 ** 20 * 1023)
    '1023 M'
    """

    # add by sim1
    if separator:
        separator = ' '

    # handle automatically_count_files false
    if byte is None:
        return ''

    if SettingsAware.settings.size_in_bytes:
        return format(byte, 'n')  # 'n' = locale-aware separator.

    # I know this can be written much shorter, but this long version
    # performs much better than what I had before.  If you attempt to
    # shorten this code, take performance into consideration.
    if byte <= 0:
        return '0'
    # mod by sim1: one decimal precision display for size
    if SettingsAware.settings.size_zero_prefix:
        if byte < 2**10:
            return '%03d.0%sB' % (byte, separator)
        if byte < 2**10 * 999:
            return '%#05.1f%sK' % ((byte / 2**10), separator)
        if byte < 2**20:
            return '%#05.1f%sK' % ((byte / 2**10), separator)
        if byte < 2**20 * 999:
            return '%#05.1f%sM' % ((byte / 2**20), separator)
        if byte < 2**30:
            return '%#05.1f%sM' % ((byte / 2**20), separator)
        if byte < 2**30 * 999:
            return '%#05.1f%sG' % ((byte / 2**30), separator)
        if byte < 2**40:
            return '%#05.1f%sG' % ((byte / 2**30), separator)
        if byte < 2**40 * 999:
            return '%#05.1f%sT' % ((byte / 2**40), separator)
        if byte < 2**50:
            return '%#05.1f%sT' % ((byte / 2**40), separator)
        if byte < 2**50 * 999:
            return '%#05.1f%sP' % ((byte / 2**50), separator)
        if byte < 2**60:
            return '%#05.1f%sP' % ((byte / 2**50), separator)
        return '>9000'

    if byte < 2**10:
        return '%d.0%sB' % (byte, separator)
    if byte < 2**10 * 999:
        return '%#.1f%sK' % ((byte / 2**10), separator)
    if byte < 2**20:
        return '%#.1f%sK' % ((byte / 2**10), separator)
    if byte < 2**20 * 999:
        return '%#.1f%sM' % ((byte / 2**20), separator)
    if byte < 2**30:
        return '%#.1f%sM' % ((byte / 2**20), separator)
    if byte < 2**30 * 999:
        return '%#.1f%sG' % ((byte / 2**30), separator)
    if byte < 2**40:
        return '%#.1f%sG' % ((byte / 2**30), separator)
    if byte < 2**40 * 999:
        return '%#.1f%sT' % ((byte / 2**40), separator)
    if byte < 2**50:
        return '%#.1f%sT' % ((byte / 2**40), separator)
    if byte < 2**50 * 999:
        return '%#.1f%sP' % ((byte / 2**50), separator)
    if byte < 2**60:
        return '%#.1f%sP' % ((byte / 2**50), separator)
    return '>9000'


def human_readable_time(timestamp):
    """Convert a timestamp to an easily readable format.
    """
    # Hard to test because it's relative to ``now()``
    date = datetime.fromtimestamp(timestamp)
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
    SettingsAware = SettingsAwareMock  # noqa: F811

    import doctest
    import sys
    sys.exit(doctest.testmod()[0])
