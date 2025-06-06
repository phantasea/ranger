# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

"""The statusbar displays information about the current file and directory.

On the left side, there is a display similar to what "ls -l" would
print for the current file.  The right side shows directory information
such as the space used by all the files in this directory.
"""

from __future__ import (absolute_import, division, print_function)

import curses
import os
from os import getuid, readlink
from pwd import getpwuid
from grp import getgrgid
from time import time, strftime, localtime

from ranger.ext.human_readable import human_readable
from ranger.gui.bar import Bar

from . import Widget


class StatusBar(Widget):  # pylint: disable=too-many-instance-attributes
    __doc__ = __doc__
    owners = {}
    groups = {}
    timeformat = '%Y-%m-%d %H:%M'
    hint = None
    msg = None

    old_thisfile = None
    old_ctime = None
    old_du = None
    old_hint = None
    result = None

    old_systime = None    # add by sim1

    def __init__(self, win, column=None):
        Widget.__init__(self, win)
        self.column = column
        self.settings.signal_bind('setopt.display_size_in_status_bar',
                                  self.request_redraw, weak=True)
        self.fm.signal_bind('tab.layoutchange', self.request_redraw, weak=True)
        self.fm.signal_bind('setop.viewmode', self.request_redraw, weak=True)

    def request_redraw(self):
        self.need_redraw = True

    def notify(self, text, duration=0, bad=False):
        self.msg = Message(text, duration, bad)

    def clear_message(self):
        self.msg = None

    def draw(self):  # pylint: disable=too-many-branches
        """Draw the statusbar"""

        if self.column != self.fm.ui.browser.main_column:
            self.column = self.fm.ui.browser.main_column
            self.need_redraw = True

        if self.hint and isinstance(self.hint, str):
            if self.old_hint != self.hint:
                self.need_redraw = True
            if self.need_redraw:
                self._draw_hint()
            return

        if self.old_hint and not self.hint:
            self.old_hint = None
            self.need_redraw = True

        if self.msg:
            if self.msg.is_alive():
                self._draw_message()
                return
            else:
                self.msg = None
                self.need_redraw = True

        if self.fm.thisfile:
            self.fm.thisfile.load_if_outdated()
            try:
                ctime = self.fm.thisfile.stat.st_ctime
            except AttributeError:
                ctime = -1
        else:
            ctime = -1

        # add by sim1
        systime = strftime('%M', localtime())

        if not self.result:
            self.need_redraw = True

        if self.old_du and not self.fm.thisdir.disk_usage:
            self.old_du = self.fm.thisdir.disk_usage
            self.need_redraw = True

        if self.old_thisfile != self.fm.thisfile:
            self.old_thisfile = self.fm.thisfile
            self.need_redraw = True

        # add by sim1
        if self.old_systime != systime:
            self.old_systime = systime
            self.need_redraw = True

        if self.old_ctime != ctime:
            self.old_ctime = ctime
            self.need_redraw = True

        if self.need_redraw:
            self.need_redraw = False

            self._calc_bar()
            self._print_result(self.result)

    def _calc_bar(self):
        bar = Bar('in_statusbar')
        self._get_left_part(bar)
        self._get_right_part(bar)
        bar.shrink_by_removing(self.wid)

        self.result = bar.combine()

    def _draw_message(self):
        self.win.erase()
        self.color('in_statusbar', 'message',
                   self.msg.bad and 'bad' or 'good')
        self.addnstr(0, 0, self.msg.text, self.wid)

    def _draw_hint(self):
        self.win.erase()
        highlight = True
        space_left = self.wid
        starting_point = self.x
        for string in self.hint.split('*'):
            highlight = not highlight
            if highlight:
                self.color('in_statusbar', 'text', 'highlight')
            else:
                self.color('in_statusbar', 'text')

            try:
                self.addnstr(0, starting_point, string, space_left)
            except curses.error:
                break
            space_left -= len(string)
            starting_point += len(string)

    #mod by sim1
    def _get_left_part(self, bar):  # pylint: disable=too-many-branches,too-many-statements
        left = bar.left
        #add by sim1: fix statusbar stopping working after switching to multipane mode
        self.column.target = self.fm.thisdir

        if self.column is not None and self.column.target is not None\
                and self.column.target.is_directory:
            target = self.column.target.pointed_obj
        else:
            directory = self.fm.thistab.at_level(0)
            if directory:
                target = directory.pointed_obj
            else:
                return
        try:
            stat = target.stat
        except AttributeError:
            #add by sim1
            left.add('empty', 'permissions')
            left.add('|', 'lspace')
            '''
            if self.settings.display_free_space_in_status_bar:
                try:
                    free = get_free_space(self.column.target.path)
                except OSError:
                    pass
                else:
                    left.add(human_readable(free, separator=''), 'size')
                    left.add('|', 'lspace')
            '''
            return
        if stat is None:
            return

        if self.fm.mode != 'normal':
            perms = '--%s--' % self.fm.mode.upper()
        else:
            perms = target.get_permission_string()
        how = 'good' if getuid() == stat.st_uid else 'bad'
        left.add('[', 'permissions')
        left.add(perms, 'permissions', how)
        left.add(']', 'permissions')
        left.add('|', 'lspace')
        #left.add(str(stat.st_nlink), 'nlink')
        #left.add('|', 'lspace')
        left.add(self._get_owner(target), 'owner')
        left.add(':', 'owner')
        left.add(self._get_group(target), 'group')

        left.add('|', 'lspace')

        try:
            date = strftime(self.timeformat, localtime(stat.st_mtime))
        except OSError:
            date = '?'
        left.add(date, 'mtime')

        left.add('|', 'lspace')

        if self._get_rating_infostring(left):
            left.add("|", "lspace")

        #del by sim1: not display vcsdate
        """
        directory = target if target.is_directory else \
            target.fm.get_directory(os.path.dirname(target.path))
        if directory.vcs and directory.vcs.track:
            if directory.vcs.rootvcs.branch:
                vcsinfo = '({0:s}: {1:s})'.format(
                    directory.vcs.rootvcs.repotype, directory.vcs.rootvcs.branch)
            else:
                vcsinfo = '({0:s})'.format(directory.vcs.rootvcs.repotype)
            left.add('|', 'lspace')
            left.add(vcsinfo, 'vcsinfo')

            left.add('|', 'lspace')
            if directory.vcs.rootvcs.obj.vcsremotestatus:
                vcsstr, vcscol = self.vcsremotestatus_symb[
                    directory.vcs.rootvcs.obj.vcsremotestatus]
                left.add(vcsstr.strip(), 'vcsremote', *vcscol)
            if target.vcsstatus:
                vcsstr, vcscol = self.vcsstatus_symb[target.vcsstatus]
                left.add(vcsstr.strip(), 'vcsfile', *vcscol)
            if directory.vcs.rootvcs.head:
                left.add('|', 'lspace')
                left.add(directory.vcs.rootvcs.head['date'].strftime(self.timeformat), 'vcsdate')
                left.add('|', 'lspace')
                summary_length = self.settings.vcs_msg_length or 50
                left.add(
                    directory.vcs.rootvcs.head['summary'][:summary_length],
                    'vcscommit'
                )
        """

    #add by sim1
    def _get_size_infostring(self, side):
        target = self.column.target
        if target is None \
                or not target.accessible \
                or (target.is_directory and target.files is None):
            return False

        if target.marked_items:
            if len(target.marked_items) == target.size:
                side.add(human_readable(target.disk_usage, separator=''), 'size')
            else:
                sumsize = sum(f.size for f in target.marked_items
                              if not f.is_directory or f.cumulative_size_calculated)
                side.add(human_readable(sumsize, separator=''), 'size')
            side.add("/" + str(len(target.marked_items)), 'size')
        else:
            size = None
            if self.settings.display_size_in_status_bar:
                try:
                    #size = os.stat(self.fm.thisfile.path).st_size
                    size = self.fm.thisfile.size
                except AttributeError:
                    size = 0
                side.add(human_readable(size, use_opt=True), 'size')

            # show size of all files in the current directory
            if self.settings.display_file_space_in_status_bar:
                if self.settings.display_size_in_status_bar:
                    side.add('/', 'size')
                size = human_readable(target.disk_usage, separator='')
                side.add(size, 'size')

            #if self.settings.display_free_space_in_status_bar:
            if size is not None:
                side.add('/', 'size')
            try:
                free = get_free_space(target.path)
            except OSError:
                side.add('ERR', 'size')
            else:
                side.add(human_readable(free, separator=''), 'size')
        return True

    #add by sim1
    def _get_rating_infostring(self, side):
        target = self.fm.thisfile.path
        stars = ''
        if self.fm.rating_info:
            for ratings in self.fm.rating_info:
                if ratings["path"] == target:
                    for i in range(int(ratings["star"])):
                        if 'DISPLAY' in os.environ:
                            stars += ''
                        else:
                            stars += '★'

                    side.add(stars, 'stars')
                    return True

        return False

    def _get_owner(self, target):
        uid = target.stat.st_uid

        try:
            return self.owners[uid]
        except KeyError:
            try:
                self.owners[uid] = getpwuid(uid)[0]
                return self.owners[uid]
            except KeyError:
                return str(uid)

    def _get_group(self, target):
        gid = target.stat.st_gid

        try:
            return self.groups[gid]
        except KeyError:
            try:
                self.groups[gid] = getgrgid(gid)[0]
                return self.groups[gid]
            except KeyError:
                return str(gid)

    #add by sim1
    def _get_symlink_infostring(self, side):
        if self.column is not None and self.column.target is not None\
                and self.column.target.is_directory:
            target = self.column.target.pointed_obj
        else:
            directory = self.fm.thistab.at_level(0)
            if directory:
                target = directory.pointed_obj
            else:
                return False

        if not target or not target.is_link:
            return False

        how = 'good' if target.exists else 'bad'
        try:
            dest = readlink(target.path)
        except OSError:
            dest = '?'
        side.add(' -> ' '"' + dest + '"', 'link', how)
        return True

    #mod by sim1
    def _get_right_part(self, bar):  # pylint: disable=too-many-branches,too-many-statements
        right = bar.right
        if self.column is None:
            return

        target = self.column.target
        if target is None \
                or not target.accessible \
                or (target.is_directory and target.files is None):
            return

        #mod by sim1
        #pos = target.scroll_begin
        #max_pos = len(target) - self.column.hei
        pos = target.pointer + 1
        max_pos = len(target.files)
        base = 'scroll'

        #add by sim1
        if not target.marked_items \
            and self._get_symlink_infostring(right):
            return

        right.add("|", "rspace")

        if self.fm.thisdir.flat:
            right.add("flat=", base, 'flat')
            right.add(str(self.fm.thisdir.flat), base, 'flat')
            right.add("|", "rspace")

        if self.fm.thisdir.narrow_filter:
            right.add("narrowed", base, 'filter')
            right.add("|", "rspace")

        if self.fm.thisdir.filter or self.fm.thisdir.inode_type_filter:
            if self.fm.thisdir.filter:
                right.add("f='", base, 'filter')
                right.add(self.fm.thisdir.filter.pattern, base, 'filter')
            else:
                right.add("only='", base, 'filter')
                right.add(self.fm.thisdir.inode_type_filter, base, 'filter')
            right.add("'", base, 'filter')
            right.add("|", "rspace")

        if self._get_size_infostring(right):
            right.add("|", "rspace")

        if target.marked_items:
            # Indicate that there are marked files. Useful if you scroll
            # away and don't see them anymore.
            right.add('Mark', base, 'marked')
        elif target.files:
            # mod by sim1: show hidden files count
            hidden_files_num = len(os.listdir(target.path)) - len(target.files)
            if self.fm.thisdir.flat or hidden_files_num == 0:
                right.add(str(target.pointer + 1) + '/' + str(len(target.files)) + ' ', base, 'ruler')
            else:
                right.add(str(target.pointer + 1) + '/' + str(len(target.files))\
                    + '(+' + str(hidden_files_num) + ')' + ' ', base, 'ruler')
            if max_pos <= self.column.hei:
                right.add('--All--', base, 'all')
            elif pos == 1:
                right.add('--Top--', base, 'top')
            elif pos >= max_pos:
                right.add('--Bot--', base, 'bot')
            else:
                #right.add('--{0:0.0%}--'.format((pos / max_pos)), base, 'percentage')
                #right.add('--{0:02.0f}%--'.format((pos*100/max_pos)), base, 'percentage')
                right.add('--{:02d}%--'.format((pos*100//max_pos)), base, 'percentage')
        else:
            #mod by sim1
            hidden_files_num = len(os.listdir(target.path)) - len(target.files)
            if (self.fm.thisdir.filter or self.fm.thisdir.inode_type_filter) \
                    and hidden_files_num > 0:
                right.add('0/0(+' + str(hidden_files_num) + ')' + ' ' + '--All--', base, 'all')
            else:
                right.add('0/0  --All--', base, 'all')

        #add by sim1: show statusline indicator for 'show_hidden'
        if self.settings.show_hidden:
            right.add("[H]", 'permissions')

        if self.settings.display_time_in_status_bar:
            right.add("|", "rspace")
            right.add('[', 'systime')
            right.add(strftime(self.timeformat, localtime()), 'systime')
            right.add(']', 'systime')

        if self.settings.freeze_files:
            # Indicate that files are frozen and will not be loaded
            right.add("|", "rspace")
            right.add('FROZEN', base, 'frozen')

    def _print_result(self, result):
        self.win.move(0, 0)
        for part in result:
            self.color(*part.lst)
            self.addstr(str(part))

        if self.settings.draw_progress_bar_in_status_bar:
            queue = self.fm.loader.queue
            states = []
            for item in queue:
                if item.progressbar_supported:
                    states.append(item.percent)
            if states:
                state = sum(states) / len(states)
                barwidth = (state / 100) * self.wid
                self.color_at(0, 0, int(barwidth), ("in_statusbar", "loaded"))
                self.color_reset()


def get_free_space(path):
    stat = os.statvfs(path)
    return stat.f_bavail * stat.f_frsize


class Message(object):  # pylint: disable=too-few-public-methods
    elapse = None
    text = None
    bad = False

    def __init__(self, text, duration, bad):
        self.text = text
        self.bad = bad
        self.elapse = time() + duration

    def is_alive(self):
        return time() <= self.elapse
