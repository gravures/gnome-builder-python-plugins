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
#       along with this program; if not, write to the Free Soipftware
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
import shutil
from pathlib import Path

import gi

from gi.repository import Gio, GLib, GObject
from gi.repository import Ide


class Python517BuildStage(Ide.PipelineStage):

    def __init__(self, build_backend, *argv, **kwargs):
        super().__init__(*argv, **kwargs)
        self.backend = build_backend
        self.set_name(
                _(f"{build_backend.get_display_name()}: building project")
            )

    def do_build_async(self, pipeline, cancellable, callback, data):
        """This is a asynchronous build stage.
        """
        task = Ide.Task.new(self, cancellable, callback)
        task.set_priority(GLib.PRIORITY_LOW)

        srcdir = pipeline.get_srcdir()
        launcher = pipeline.create_launcher()
        launcher.set_cwd(srcdir)

        context = pipeline.get_context()
        build_system = Ide.BuildSystem.from_context(context)
        _venv = None
        if not self.backend.has_isolation():
           _venv = build_system.get_virtual_env()

        for i, arg in enumerate(self.backend.get_build_cmd()):
            if i==0 and _venv:
                arg = f"{_venv}/bin/{arg}"
            launcher.push_argv(arg)

        task.connect("notify::completed", self._build_completed_cb)
        self.set_active(True)
        pipeline.attach_pty(launcher)
        self.log(Ide.BuildLogStream.STDOUT, " ".join(self.backend.get_build_cmd()), -1)

        # launch the process
        subprocess = launcher.spawn(cancellable)
        if subprocess is None:
            task.return_error(
                GLib.Error(
                    "build subprocess failed",
                    domain=GLib.quark_to_string(GLib.spawn_error_quark()),
                    code=GLib.SpawnError.FAILED,
                )
            )
            return
        subprocess.wait_async(cancellable, self._wait_cb, task)

    def _wait_cb(self, subprocess, result, task):
        exit_status = subprocess.get_exit_status()
        if exit_status > 0:
            task.return_error(GLib.Error(
                    f"build subprocess exit with signal {exit_status}",
                    domain=GLib.quark_to_string(GLib.spawn_error_quark()),
                    code=GLib.SpawnError.FAILED,
                )
            )
            return
        task.return_boolean(True)

    def _build_completed_cb(self, task, _pspec):
        # FIXME: build target ui not updated until collapsing
        # and expand target
        context = self.get_context()
        build_system = Ide.BuildSystem.from_context(context)
        build_dir = Path(build_system.get_builddir())
        if build_dir.is_dir():
            for file in build_dir.iterdir():
                build_system.add_build(file)
        self.set_active(False)

    def do_build_finish(self, task):
        return task.propagate_boolean()

    def do_clean_async(self, pipeline, cancellable, callback, data):
        """
        When the user requests that the build pipeline run the
        clean operation (often before a "rebuild"), this function
        will be executed. Use it to delete stale directories, etc.
        """
        task = Ide.Task.new(self, cancellable, callback)
        task.set_priority(GLib.PRIORITY_LOW)
        task.connect("notify::completed", self._clean_completed_cb)
        self.set_active(True)
        self.log(
            Ide.BuildLogStream.STDOUT,
            f"cleaning {self.backend.get_builddir_name()} directory",
            -1,
        )

        build_dir = Path(pipeline.get_builddir())
        if build_dir.is_dir():
            files = [child for child in build_dir.iterdir()]
            for file in files:
                if file.is_file():
                    self.log(
                        Ide.BuildLogStream.STDOUT, f"deleting {file.name}",-1,
                    )
                    file.unlink()
                if file.is_dir():
                    self.log(
                        Ide.BuildLogStream.STDOUT,
                        f"deleting {file.name} directory tree",
                        -1,
                    )
                    shutil.rmtree(file, ignore_errors=True)
        task.return_boolean(True)

    def _clean_completed_cb(self, task, _pspec):
        # FIXME: build target ui not updated until collapsing
        # and expand target
        context = self.get_context()
        build_system = Ide.BuildSystem.from_context(context)
        build_system.clean_builds()
        self.set_active(False)

    def do_clean_finish(self, task):
        return task.propagate_boolean()

    def do_query(self, pipeline, cancellable):
        """
        If you need to check if this stage still needs to
        be run, use the query signal to check an external
        resource.

        By default, stages are marked completed after they
        run. That means a second attempt to run the stage
        will be skipped unless set_completed() is set to False.

        If you need to do something asynchronous, call
        self.pause() to pause the stage until the async
        operation has completed, and then call unpause()
        to resume execution of the stage.
        """
        # This will run on every request to run the phase
        self.set_completed(False)

    def do_chain(self, _next):
        """
        Sometimes, you have build stages that are next to
        each other in the pipeline and they can be coalesced
        into a single operation.

        One such example is "make" followed by "make install".

        You can detect that here and reduce how much work is
        done by the build pipeline.
        """
        return False

#EOF
