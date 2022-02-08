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
#       along with this program; if not, write to the Free Soipftware
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
from abc import ABC, abstractmethod
from pathlib import Path
import shutil
import venv

import gi

from gi.repository import Gio, GLib, GObject
from gi.repository import Ide

import tomli


_ = Ide.gettext


class Python517BuildSystemDiscovery(Ide.SimpleBuildSystemDiscovery):
    """SimpleBuildSystemDiscovery subclass.

    The "glob" property is a glob to match for files within the project
    directory. This can be used to quickly match the project file, such as
    "configure.*".
    The "hint" property is used from ide_build_system_discovery_discover()
    if the build file was discovered.
    The "priority" property is the priority of any match.

    All of those Ide.SimpleBuildSystemDiscovery property
    are available since ABI 3.32
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.glob = "pyproject.toml"
        self.props.hint = "python_517_build_plugin"
        self.props.priority = 500


class Python517BuildBackend(ABC):

    def get_name(self):
        """Return the canonic name of the backend."""
        return self.__name__

    @abstractmethod
    def get_display_name(self):
        """Return a string to show in the ui."""
        pass

    @abstractmethod
    def get_builddir_name(self):
        return "build"

    def get_builddir(self, root_dir):
        """A method returning the path used as the build directory
        for this Backend.

        Args:
            root_dir(Gio.File): the root directory for the project.

        Returns(Gio.File): the build directory path for this Backend.
        """
        return root_dir.get_child(self.get_builddir_name())

    @abstractmethod
    def get_build_argv(self):
        """Gets the arguments used to run the build.

        Returns(list): a list containing the arguments to run the build.
        """
        pass

    @abstractmethod
    def get_clean_argv(self):
        """."""
        pass


class PypaBuildBackend(Python517BuildBackend):
    """PypaBuildBackend. """

    def get_display_name(self):
        return "Pypa Build"

    def get_builddir_name(self):
        return "dist"

    def get_build_argv(self):
        return ["python",
                "-m",
                "build",
                "--sdist",
                "--outdir",
                self.get_builddir_name(),
        ]

    def get_clean_argv(self):
        # TODO: develop
        return []


class Python517BuildSystem(Ide.Object, Ide.BuildSystem, Gio.AsyncInitable):
    """A Python Pep 517 BuildSystem.

    In certain circumstances, projects may wish to include the source code
    for the build backend directly in the source tree, rather than referencing
    the backend via the requires key.
    Projects can specify that their backend code is hosted in-tree by including
    the backend-path key in pyproject.toml.
        * Directories in backend-path are interpreted as relative to the project
          root, and MUST refer to a location within the source tree
        * The backend code MUST be loaded from one of the directories specified
          in backend-path

    All of those Ide.BuildSystem methods and property
    are available since ABI 3.32
    """
    project_file = GObject.Property(type=Gio.File)  # 'pyproject.toml'
    backends = GObject.Property(
                    type=GLib.HashTable,
                    default={"setuptools.build_meta": PypaBuildBackend},
                    flags = GObject.ParamFlags.READABLE,
               )
    #requires = GObject.Property(type=GLib.List, default=[])
    #backend_path = GObject.Property(type=GLib.List, default=[])
    frontend = GObject.Property(type=str, default="pip")
    build_backend = GObject.Property(type=object, default=None)


    def do_init_async(self, priority, cancel, callback, data=None):
        task = Gio.Task.new(self, cancel, callback)
        task.set_priority(priority)
        # parse project_file
        project_file = self.get_pyproject_toml()
        project_file.load_contents_async(
            cancel,
            self._on_load_pyproject_toml,
            task,
        )

    def do_init_finish(self, result):
        return result.propagate_boolean()

    def _on_load_pyproject_toml(self, project_file, result, task):
        """Load and parse the pyproject.toml file.

        If the pyproject.toml file is absent, or the build-backend key is missing,
        the source tree is not using Pep517 specification. Tools should revert
        to the legacy behaviour of running setup.py (either directly,
        or by implicitly invoking the setuptools.build_meta:__legacy__ backend).
        Where the build-backend key exists, this takes precedence and the source
        tree follows the format and conventions of the specified backend
        (as such no setup.py is needed unless the backend requires it).
        """
        print("\nPython517Build._on_load_pyproject_toml()")

        try:
            ok, contents, _etag = project_file.load_contents_finish(result)
        except GLib.Error as e:  # IOError
            task.return_error(e)
            return

        try:
            py_project = tomli.loads(contents.decode('utf-8'))
        except tomli.TOMLDecodeError as e:  # Invalid toml file
            task.return_error(e)
            return

        if "build-system" not in py_project \
            or not isinstance(py_project["build-system"], dict) \
            or "build-backend" not in py_project["build-system"] \
            or not isinstance(py_project["build-system"]["build-backend"], str):
            # Not a PEP 517 python project
            task.return_error(
                GLib.Error(
                    "Not a valid python PEP-517 build system",
                    domain=GLib.quark_to_string(Gio.io_error_quark()),
                    code=Gio.IOErrorEnum.NOT_SUPPORTED,
                )
            )
            return

        _backend = self.props.backends.get(
                    py_project["build-system"]["build-backend"]
                )
        if _backend:
            self.props.build_backend = _backend()

        task.return_boolean(True)

    def get_pyproject_toml(self):
        """Return the 'pyproject.toml' file.

        Returns(Gio.File): the 'pyproject.toml' file
        """
        if self.props.project_file.get_basename() != 'pyproject.toml':
            return self.props.project_file.get_child('pyproject.toml')
        else:
            return self.props.project_file

    def do_get_project_version(self):
        """If the build system supports it, gets the project
        version as configured in the build system's configuration files.

        Returns(str): a string containing the project version
        """
        # TODO: develop
        return None

    def do_build_system_supports_language(self, language):
        """Say if this BuilSystem support 'language'.

        Returns True if self in it's current configuration
        is known to support 'language'.
        """
        return language == "python3"

    def do_get_builddir(self, pipeline):
        """Return a path to the build directory.

        This path may not be the same for different
        build backend, so ask to the backend what is
        its build directory.

        Returns(str): A path representing the build directory.
        """
        if self.props.build_backend is None:
            return self.get_context().ref_workdir().get_path()
        else:
            _wd = self.get_context().ref_workdir()
            return self.props.build_backend.get_builddir(_wd).get_path()

    def do_get_id(self):
        return "python_517_build_system"

    def do_get_display_name(self):
        return "Python (pyproject.toml)"

    def do_get_priority(self):
        return 500


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
        task = Ide.Task.new(self, cancellable, callback, data)
        #task.set_source_tag(self.do_build_async)
        task.set_priority(GLib.PRIORITY_LOW)

        srcdir = pipeline.get_srcdir()
        launcher = pipeline.create_launcher()
        launcher.set_cwd(srcdir)
        for arg in self.backend.get_build_argv():
            launcher.push_argv(arg)

        task.connect("notify::completed", self._notify_completed_cb)
        self.set_active(True)
        pipeline.attach_pty(launcher)
        self.log(Ide.BuildLogStream.STDOUT, " ".join(self.backend.get_build_argv()), -1)

        # launch the process
        subprocess = launcher.spawn(cancellable)
        if subprocess is None:
            task.return_error(
                GLib.Error(
                    "build subprocess failed",
                    domain=GLib.quark_to_string(GLib.spawn_error_quark()),
                    code=GLib.SpawnErrorEnum.FAILED,
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
                    code=GLib.SpawnErrorEnum.FAILED,
                )
            )
            return
        task.return_boolean(True)

    def _notify_completed_cb(self, task, _p):
        self.set_active(False)

    def do_build_finish(self, task):
        return task.propagate_boolean()

    def do_clean_async(self, pipeline, cancellable, callback, data):
        """
        When the user requests that the build pipeline run the
        clean operation (often before a "rebuild"), this function
        will be executed. Use it to delete stale directories, etc.
        """
        task = Ide.Task.new(self, cancellable, callback, data)
        #task.set_source_tag(self.do_clean_async)
        task.set_priority(GLib.PRIORITY_LOW)

        task.connect("notify::completed", self._notify_completed_cb)
        self.set_active(True)
        self.log(
            Ide.BuildLogStream.STDOUT,
            f"cleaning {self.backend.get_builddir_name()} directory",
            -1,
        )

        build_dir = Path(self.pipeline.get_builddir())
        if build_dir.is_dir():
            files = [child for child in p.iterdir()]
            for file in files:
                if file.is_file():
                    file.unlink()
                if file.is_dir():
                    shutil.rmtree(file, ignore_errors=True)
        task.return_boolean(True)

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

    def do_chain(self, next):
        """
        Sometimes, you have build stages that are next to
        each other in the pipeline and they can be coalesced
        into a single operation.

        One such example is "make" followed by "make install".

        You can detect that here and reduce how much work is
        done by the build pipeline.
        """
        return False


class Python517PipelineAddin(Ide.Object, Ide.PipelineAddin):
    """
    Builder uses the concept of a “Build Pipeline” to build a project.
    The build pipeline consistes of multiple “phases” and build “stages”
    run in a given phase.
    The Ide.Pipeline is used to specify how and when build operations
    should occur. Plugins attach build stages to the pipeline to perform
    build actions.
    The Python517PipelineAddin registers those stages to be executed
    when various phases of the build pipeline are requested.
    """

    def do_load(self, pipeline):
        context = pipeline.get_context()
        build_system = Ide.BuildSystem.from_context(context)

        # Only register stages if we are a pyproject.toml
        if not isinstance(build_system, Python517BuildSystem):
            return

        build_backend = build_system.get_property("build_backend")
        build_stage = Python517BuildStage(build_backend)
        phase = Ide.PipelinePhase.BUILD | Ide.PipelinePhase.AFTER
        stage_id = pipeline.attach(phase, 100, build_stage)
        self.track(stage_id)


class Python517BuildTarget(Ide.Object, Ide.BuildTarget):
    """Python517BuildTarget.

    Ide.BuildTarget API is available since ABI 3.32
    """

    def do_get_install_directory(self):
        """Returns(Gio.File): a GFile or None."""
        # TODO: develop
        # sys.executable return python path following venv
        return None

    def do_get_display_name(self):
        """A display name for the build target
        to be displayed in UI. May contain pango markup.

        Returns(str): A display name.
        """
        return "Pypa Build"

    def do_get_name(self):
        """Return a command name.

        Returns(str): A command name (a filename) or None.
        """
        return "python"

    def do_get_priority(self):
        """Gets the priority of the build target.

        This is used to sort build targets by their importance.
        The lowest value (negative values are allowed) will be run
        as the default run target by Builder.

        Returns(int): the priority of the build target
        """
        return 500

    def do_get_argv(self):
        """Gets the arguments used to run the target.

        Returns(str): containing the arguments to run the target.
        """
        return ["python"]

    def do_get_cwd(self):
        """Gets the correct working directory.

        For build systems and build target providers that insist
        to be run in a specific place, this method gets the correct
        working directory.
        If this method returns None, the runtime will pick a default
        working directory for the spawned process (usually, the user
        home directory in the host system, or the flatpak sandbox
        home under flatpak).

        Returns(str): the working directory to use for this target
        """
        context = self.get_context()
        project_file = Ide.BuildSystem.from_context(context).project_file
        if project_file.query_file_type(0, None) == Gio.FileType.DIRECTORY:
            return project_file.get_path()
        else:
            return project_file.get_parent().get_path()

    def do_get_language(self):
        """Return the programming language of this build target.

        Return the main programming language that was used to
        write this build target.
        This method is primarily used to choose an appropriate
        debugger. Therefore, if a build target is composed of
        components in multiple language (eg. a GJS app with
        GObject Introspection libraries, or a Java app with JNI
        libraries), this should return the language that is
        most likely to be appropriate for debugging.
        The default implementation returns "asm", which indicates
        an unspecified language that compiles to native code.

        Returns(str): the programming language of this target
        """
        return "python3"

    def do_get_kind(self):
        """Gets the kind of artifact.

        Returns(Ide.ArtifactKind): an IdeArtifactKind
        """
        return Ide.ArtifactKind.EXECUTABLE

    def do_get_install(self):
        """Checks if the Ide.BuildTarget gets installed.

        Returns(bool): TRUE if the build target is installed
        """
        # TODO: develop
        return True


class Python517BuildTargetProvider(Ide.Object, Ide.BuildTargetProvider):
    """PythonBuildTargetProvider.

    Ide.BuildTargetProvider API is available since ABI 3.32
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("\nPython517BuildTargetProvider")

    def do_get_targets_async(self, cancellable, callback, data):
        """Asynchronously requests that the provider fetch all
        of the known build targets that are part of the project.
        Generally this should be limited to executables that Builder
        might be interested in potentially running.
        'callback' should call ide_build_target_provider_get_targets_finish()
        to complete the asynchronous operation.

        Args:
            cancellable(GCancellable): a GCancellable or None
            callback(callable): a callback to execute upon completion
            user_data: closure data for callback
        """
        print("\nPython517BuildTargetProvider.do_get_targets_async()")
        task = Ide.Task.new(self, cancellable, callback)
        task.set_priority(GLib.PRIORITY_LOW)

        context = self.get_context()
        build_system = Ide.BuildSystem.from_context(context)

        if not isinstance(build_system, Python517BuildSystem):
            task.return_error(
                GLib.Error(
                    "Not a python 517 build system",
                    domain=GLib.quark_to_string(Gio.io_error_quark()),
                    code=Gio.IOErrorEnum.NOT_SUPPORTED,
                )
            )
            return

        task.targets = [build_system.ensure_child_typed(Python517BuildTarget)]
        task.return_boolean(True)

    def do_get_targets_finish(self, result):
        """Completes a request to get the targets for the project.

        Args:
            result(GAsyncResult): a GAsyncResult provided to the callback

        Returns(list): A list of Ide.BuildTarget or None upon failure
                       and error is set.
        """
        if result.propagate_boolean():
            return result.targets


# EOF
