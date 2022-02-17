#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#       Copyright (c) Gilles Coissac 2022 <info@gillescoissac.fr>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
import gi  # noqa
from gi.repository import Gio, GLib, GObject, Ide

VERSION_HOOK = """import @MODULE@

print(@MODULE@.__version__)
"""


class ISortPageAddin(Ide.Object, Ide.EditorPageAddin):
    __gtype_name__ = "ISortPageAddin"
    __version = None
    __gproperties__ = {
        "version": (str, "isort version", "a string version identifier", "",
                    GObject.ParamFlags.READABLE)
    }

    # Fake a gproperty class attribute because:
    # firstly we can´t have a reliable __new__ method with
    # GObject subclassing and secondly virtual method overload
    # (the do_method) could be called before any __init__ method
    # will be reached.
    # So this seems to be the only way to safely initialize
    # some attributes before any call to the instance methods.
    def do_get_property(self, prop):
        if prop.name == 'version':
            if self.__version is None:
                ret = self.__class__.__get_version()
                self.__class__.__version = ret if ret else None
                self.version = ret if ret else "unavailable"
            else:
                self.version = self.__class__.__version
            return self.version
        else:
            raise AttributeError('unknown property %s' % prop.name)

    @classmethod
    def __get_version(cls):
        try:
            launcher = Ide.SubprocessLauncher()
            launcher.set_flags(
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDIN_PIPE
            )
            launcher.set_run_on_host(True)
            launcher.push_args(['python', '-'])
            subprocess = launcher.spawn()
            stdin = VERSION_HOOK.replace(
                "@MODULE@",
                cls.get_cmd_name(),
                2
            )
            success, stdout, stderr = subprocess.communicate_utf8(stdin, None)
            if not success:
                return None
            return stdout
        except GLib.Error:
            return None

    @staticmethod
    def get_cmd_name():
        return "isort"

    def do_load(self, page: Ide.EditorPage):
        if self.props.version == "unavailable":
            print("DEBUG: isort not found")
            return

        # Register action & callback
        self.isort_action = Gio.SimpleAction.new("sort-import", None)
        self.isort_action.connect("activate", self._sort_import_cb)
        group = Gio.SimpleActionGroup()
        group.insert(self.isort_action)
        self.page = page
        self.page.insert_action_group("python-isort", group)

        lang = self.page.get_language_id()
        if lang != 'python3':
            self.isort_action.set_enabled(False)

    def do_unload(self, page: Ide.EditorPage):
        """This should undo anything we setup when loading the addin.
        """
        page.insert_action_group("python-isort", None)

    def do_language_changed(self, lang_id: str):
        if lang_id == 'python3':
            self.isort_action.set_enabled(True)

    def _sort_import_cb(self, action: Gio.SimpleAction, data: object):
        source_view = self.page.get_view()
        if not isinstance(source_view, Ide.SourceView):
            return

        # check if source is editable
        editable = source_view.get_editable()
        if not editable:
            return

        # Block user interaction on editor
        buffer = self.page.get_buffer()
        completion = source_view.get_completion()
        completion.block_interactive()
        buffer.begin_user_action()

        # create subprocess launcher
        context = self.get_context()
        srcdir = context.ref_workdir().get_path()
        launcher = Ide.SubprocessLauncher()
        launcher.set_flags(
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDIN_PIPE
        )
        launcher.set_cwd(srcdir)

        # do the thing
        file = self.page.get_file()
        start, end = buffer.get_bounds()
        utf8_code = buffer.get_text(start, end, True)
        sorted_code = self._get_sorted_code(launcher, file, utf8_code)
        if sorted_code is not None:
            buffer.set_text(sorted_code, len(sorted_code) + 1)

        # unblock user interaction
        buffer.end_user_action()
        completion.unblock_interactive()

    def _get_sorted_code(
        self, launcher: Ide.SubprocessLauncher, file: Gio.File, buffer: str
    ):
        file_name = file.get_path()
        isort = ISortPageAddin.get_cmd_name()

        gsetttings = Gio.Settings.new_with_path(
            "org.gnome.builder.editor.language",
            "/org/gnome/builder/editor/language/python3/"
        )
        max_line_length = str(gsetttings.get_int("right-margin-position"))
        indent_size = str(gsetttings.get_int("tab-width"))

        try:
            launcher.push_args(
                ['python',
                 '-m', isort,
                 '--indent', indent_size,
                 '--line-length', max_line_length,
                 # --virtual-env  # TODO
                 '--py', 'auto',  # FIXME
                 # TODO: black compat
                 '--stdout',
                 '--filename', file_name,
                 '-']
            )
            subprocess = launcher.spawn()
            success, stdout, stderr = subprocess.communicate_utf8(buffer, None)
            if not success:
                return None
            return stdout
        except GLib.Error:
            return None
