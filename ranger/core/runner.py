# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

"""This module is an abstract layer over subprocess.Popen

It gives you highlevel control about how processes are run.

Example:
run = Runner(logfunc=print)
run('sleep 2', wait=True)         # waits until the process exists
run(['ls', '--help'], flags='p')  # pipes output to pager
run()                             # prints an error message

List of allowed flags:
s: silent mode. output will be discarded.
f: fork the process.
p: redirect output to the pager
c: run only the current file (not handled here)
l: clear screen before running
w: wait for enter-press afterwards
r: run application with root privilege (requires sudo)
t: run application in a new terminal window
(An uppercase key negates the respective lower case flag)
"""

from __future__ import (absolute_import, division, print_function)

import logging
import os
import sys
from io import open
from subprocess import Popen, PIPE, STDOUT

from ranger.ext.get_executables import get_executables, get_term
from ranger.ext.popen_forked import Popen_forked


LOG = logging.getLogger(__name__)


# TODO: Remove unused parts of runner.py
# ALLOWED_FLAGS = 'sdpwcrtSDPWCRT'
ALLOWED_FLAGS = 'cfrtCFRTlx'   #mod by sim1: add flags 'lx'


def press_enter():
    """Wait for an ENTER-press"""
    sys.stdout.write("Press ENTER to continue")
    try:
        waitfnc = raw_input
    except NameError:
        # "raw_input" not available in python3
        waitfnc = input
    waitfnc()


class Context(object):  # pylint: disable=too-many-instance-attributes
    """A context object contains data on how to run a process.

    The attributes are:
    action -- a string with a command or a list of arguments for
        the Popen call.
    app -- the name of the app function. ("vim" for app_vim.)
        app is used to get an action if the user didn't specify one.
    mode -- a number, mainly used in determining the action in app_xyz()
    flags -- a string with flags which change the way programs are run
    files -- a list containing files, mainly used in app_xyz
    file -- an arbitrary file from that list (or None)
    fm -- the filemanager instance
    wait -- boolean, wait for the end or execute programs in parallel?
    popen_kws -- keyword arguments which are directly passed to Popen
    """

    def __init__(  # pylint: disable=redefined-builtin,too-many-arguments
        self,
        *,
        action=None,
        app=None,
        mode=None,
        flags=None,
        files=None,
        file=None,
        fm=None,
        wait=None,
        popen_kws=None
    ):
        self.action = action
        self.app = app
        self.mode = mode
        self.flags = flags
        self.files = files
        self.file = file
        self.fm = fm
        self.wait = wait
        self.popen_kws = popen_kws

    @property
    def filepaths(self):
        try:
            return [f.path for f in self.files]
        except AttributeError:
            return []

    def __iter__(self):
        """Iterate over file paths"""
        for item in self.filepaths:
            yield item

    def squash_flags(self):
        """Remove duplicates and lowercase counterparts of uppercase flags"""
        for flag in self.flags:
            if ord(flag) <= 90:
                bad = flag + flag.lower()
                self.flags = ''.join(c for c in self.flags if c not in bad)


class Runner(object):  # pylint: disable=too-few-public-methods

    def __init__(self, ui=None, logfunc=None, fm=None):
        self.ui = ui
        self.fm = fm
        self.logfunc = logfunc
        self.zombies = set()

    def _log(self, text):
        try:
            self.logfunc(text)
        except TypeError:
            pass
        return False

    def _activate_ui(self, boolean):
        if self.ui is not None:
            if boolean:
                try:
                    self.ui.initialize()
                except Exception as ex:  # pylint: disable=broad-except
                    self._log("Failed to initialize UI")
                    LOG.exception(ex)
            else:
                try:
                    self.ui.suspend()
                except Exception as ex:  # pylint: disable=broad-except
                    self._log("Failed to suspend UI")
                    LOG.exception(ex)

    def __call__(
        # pylint: disable=too-many-branches,too-many-statements
        # pylint: disable=too-many-arguments,too-many-locals
        self,
        action=None,
        *,
        try_app_first=False,
        app='default',
        files=None,
        mode=0,
        flags='',
        wait=True,
        **popen_kws
    ):
        """Run the application in the way specified by the options.

        Returns False if nothing can be done, None if there was an error,
        otherwise the process object returned by Popen().

        This function tries to find an action if none is defined.
        """

        # Find an action if none was supplied by
        # creating a Context object and passing it to
        # an Application object.

        context = Context(app=app, files=files, mode=mode, fm=self.fm,
                          flags=flags, wait=wait, popen_kws=popen_kws,
                          file=files and files[0] or None)

        if action is None:
            return self._log("No way of determining the action!")

        # Preconditions

        context.squash_flags()
        popen_kws = context.popen_kws  # shortcut

        toggle_ui = True
        pipe_output = False
        clear_screen = False
        wait_for_enter = False
        devnull = None

        if 'shell' not in popen_kws:
            popen_kws['shell'] = isinstance(action, str)

        # Set default shell for Popen
        if popen_kws['shell']:
            # This doesn't work with fish, see #300
            if 'fish' not in os.environ['SHELL']:
                popen_kws['executable'] = os.environ['SHELL']

        if 'stdout' not in popen_kws:
            popen_kws['stdout'] = sys.stdout
        if 'stderr' not in popen_kws:
            popen_kws['stderr'] = sys.stderr

        # Evaluate the flags to determine keywords
        # for Popen() and other variables

        if 'p' in context.flags:
            popen_kws['stdout'] = PIPE
            popen_kws['stderr'] = STDOUT
            toggle_ui = False
            pipe_output = True
            context.wait = False
        if 's' in context.flags:
            # Using a with-statement for these is inconvenient.
            # pylint: disable=consider-using-with
            devnull_writable = open(os.devnull, 'w', encoding="utf-8")
            devnull_readable = open(os.devnull, 'r', encoding="utf-8")
            for key in ('stdout', 'stderr'):
                popen_kws[key] = devnull_writable
            toggle_ui = False
            popen_kws['stdin'] = devnull_readable
        if 'f' in context.flags:
            toggle_ui = False
            context.wait = False
        if 'l' in context.flags:
            clear_screen = True
        if 'w' in context.flags:
            if not pipe_output and context.wait:  # <-- sanity check
                wait_for_enter = True
        if 'r' in context.flags:
            # TODO: make 'r' flag work with pipes
            if 'sudo' not in get_executables():
                return self._log("Can not run with 'r' flag, sudo is not installed!")
            f_flag = ('f' in context.flags)
            if isinstance(action, str):
                action = 'sudo ' + (f_flag and '-b ' or '') + action
            else:
                action = ['sudo'] + (f_flag and ['-b'] or []) + action
            toggle_ui = True
            context.wait = True
        if 't' in context.flags:
            if not ('WAYLAND_DISPLAY' in os.environ
                    or sys.platform == 'darwin'
                    or 'DISPLAY' in os.environ):
                return self._log("Can not run with 't' flag, no display found!")
            term = get_term()
            if isinstance(action, str):
                action = term + ' -e ' + action
            else:
                action = [term, '-e'] + action
            toggle_ui = False
            context.wait = False

        popen_kws['args'] = action
        # Finally, run it

        if toggle_ui:
            self._activate_ui(False)

        error = None
        process = None

        try:
            self.fm.signal_emit('runner.execute.before',
                                popen_kws=popen_kws, context=context)
            if clear_screen:
                Popen(['cls' if os.name == 'nt' else 'clear'])
            try:
                if 'f' in context.flags and 'r' not in context.flags:
                    # This can fail and return False if os.fork() is not
                    # supported, but we assume it is, since curses is used.
                    # pylint: disable=consider-using-with
                    Popen_forked(**popen_kws)
                else:
                    process = Popen(**popen_kws)
            except OSError as ex:
                error = ex
                self._log("Failed to run: %s\n%s" % (str(action), str(ex)))
            else:
                if context.wait:
                    process.wait()
                elif process:
                    self.zombies.add(process)
                if wait_for_enter:
                    press_enter()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        self.fm.signal_emit('runner.execute.after',
                            popen_kws=popen_kws, context=context, error=error)
        if devnull:
            devnull.close()
        if toggle_ui:
            self._activate_ui(True)
        if pipe_output and process:
            #add by sim1 -------------------------------------------------
            #for clipboard_paste
            if 'x' in context.flags:
                return process  # pylint: disable=lost-exception
            #for output on cmdline
            if 'b' in context.flags:
                self.fm.notify("%s" % process.stdout.readline().decode('utf8').rstrip("\n"), bad=False)
                return process  # pylint: disable=lost-exception
            #add by sim1 +++++++++++++++++++++++++++++++++++++++++++++++++

            return self(action='less', app='pager',
                        try_app_first=True, stdin=process.stdout)
        return process
