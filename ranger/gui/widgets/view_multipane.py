# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

import curses
from ranger.gui.widgets.view_base import ViewBase
from ranger.gui.widgets.browsercolumn import BrowserColumn
from ..displayable import DisplayableContainer


class ViewMultipane(ViewBase):

    def __init__(self, win):
        ViewBase.__init__(self, win)

        self.fm.signal_bind('tab.layoutchange', self._layoutchange_handler)
        self.fm.signal_bind('tab.change', self._tabchange_handler)
        self.rebuild()
        
        self.old_draw_borders = self.settings.draw_borders

    def _layoutchange_handler(self):
        if self.fm.ui.browser == self:
            self.rebuild()

    def _tabchange_handler(self, signal):
        if self.fm.ui.browser == self:
            if signal.old:
                signal.old.need_redraw = True
            if signal.new:
                signal.new.need_redraw = True
            self.rebuild()

    def rebuild(self):
        self.columns = []
        self.container = []

        for name, tab in self.fm.tabs.items():
            column = BrowserColumn(self.win, 0, tab=tab)
            column.main_column = True
            column.display_infostring = True
            if name == self.fm.current_tab:
                self.main_column = column
            self.columns.append(column)
            self.add_child(column)
        self.resize(self.y, self.x, self.hei, self.wid)

    def resize(self, y, x, hei=None, wid=None):
        ViewBase.resize(self, y, x, hei, wid)
        column_width = int((wid - len(self.columns) + 1) / len(self.columns))
        left = 0
        top = 0
        for column in self.columns:
            column.resize(top, left, hei, max(1, column_width))
            left += column_width + 1
            column.need_redraw = True
        self.need_redraw = True

    def _draw_borders(self, border_types):
        win = self.win

        self.color('in_browser', 'border')
        for child in self.columns[:-1]:
            if 'separators' in border_types or 'outline' in border_types:
                try:
                    #win.vline(0, child.x + child.wid, curses.ACS_VLINE, self.hei)
                    win.vline(0, child.x + child.wid, '|', self.hei)
                except curses.error:
                    pass

    def draw(self):
        if self.need_clear:
            self.win.erase()
            self.need_redraw = True
            self.need_clear = False
        for tab in self.fm.tabs.values():
            directory = tab.thisdir
            if directory:
                directory.load_content_if_outdated()
                directory.use()
        DisplayableContainer.draw(self)
        if self.settings.draw_borders:
            draw_borders = self.settings.draw_borders.lower()
            if draw_borders in ['both', 'true']:
                border_types = ['separators', 'outline']
            else:
                border_types = [draw_borders]
            self._draw_borders(border_types)
        if self.draw_bookmarks:
            self._draw_bookmarks()
        elif self.draw_hints:
            self._draw_hints()
        elif self.draw_info:
            self._draw_info(self.draw_info)

    def poke(self):
        ViewBase.poke(self)

        if self.old_draw_borders != self.settings.draw_borders:
            self.resize(self.y, self.x, self.hei, self.wid)
            self.old_draw_borders = self.settings.draw_borders
