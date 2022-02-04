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
from enum import Enum

import gi

from gi.repository import Gio, GLib, GObject
from gi.repository import Ide


_ = Ide.gettext


class ArtifactKind(Enum):
    """ArtifactKind enumeration.

    This class map the enum Ide for documentation purpose.
    """

    NONE = Ide.ArtifactKind.IDE_ARTIFACT_KIND_NONE
    EXECUTABLE = Ide.ArtifactKind.IDE_ARTIFACT_KIND_EXECUTABLE
    SHARED_LIBRARY = Ide.ArtifactKind.IDE_ARTIFACT_KIND_SHARED_LIBRARY
    STATIC_LIBRARY = Ide.ArtifactKind.IDE_ARTIFACT_KIND_STATIC_LIBRARY
    FILE = Ide.ArtifactKind.IDE_ARTIFACT_KIND_FILE


class PythonBuildSystemDiscovery(Ide.SimpleBuildSystemDiscovery):
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
        self.props.hint = "python_build_plugin"
        self.props.priority = 500


class PythonBuildSystem(Ide.Object, Ide.BuildSystem):
    """PythonBuildSystem.

    All of those Ide.BuildSystem methods and property
    are available since ABI 3.32
    """
    # our pyproject.toml file
    project_file = GObject.Property(type=Gio.File)

    def do_get_project_version(self):
        """If the build system supports it, gets the project
        version as configured in the build system's configuration files.

        Returns(str): a string containing the project version
        """
        return None

    def do_build_system_supports_language(self, language):
        """Say if this BuilSystem support 'language'.

        Returns True if self in it's current configuration
        is known to support 'language'.
        """
        return language == "python3"

    def do_get_builddir(self, pipeline):
        return self.get_context().ref_workdir().get_path()

    def do_get_id(self):
        return "python_build"

    def do_get_display_name(self):
        return "Python Build System"

    def do_get_priority(self):
        return 500


class PythonBuildTarget(Ide.Object, Ide.BuildTarget):
    """The build system has to know how to find build targets
    (binaries or scripts that are installed) for the runner to work.

    Ide.BuildTarget API is available since ABI 3.32
    """

    def do_get_install_directory(self):
        """Returns(Gio.File): a GFile or None."""
        return None

    def do_get_display_name(self):
        """A display name for the build target
        to be displayed in UI. May contain pango markup.

        Returns(str): A display name.
        """
        return "Python Build"

    def do_get_name(self):
        """Return a filename.

        Returns(str): A filename or None."""
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
        return ["python", "-m", "build"]

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
        return None


class PythonBuildTargetProvider(Ide.Object, Ide.BuildTargetProvider):
    """PythonBuildTargetProvider.

    Ide.BuildTargetProvider API is available since ABI 3.32
    """

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
        task = Ide.Task.new(self, cancellable, callback)
        task.set_priority(GLib.PRIORITY_LOW)

        context = self.get_context()
        build_system = Ide.BuildSystem.from_context(context)

        if not isinstance(build_system, PythonBuildSystem):
            task.return_error(
                GLib.Error(
                    "Not a python build system",
                    domain=GLib.quark_to_string(Gio.io_error_quark()),
                    code=Gio.IOErrorEnum.NOT_SUPPORTED,
                )
            )
            return

        task.targets = [build_system.ensure_child_typed(PythonBuildTarget)]
        task.return_boolean(True)

    def do_get_targets_finish(self, result, error):
        """Completes a request to get the targets for the project.

        Args:
            result(GAsyncResult): a GAsyncResult provided to the callback
            error: a location for a GError, or None

        Returns(list): A list of Ide.BuildTarget or None upon failure
                       and error is set.
        """
        if result.propagate_boolean():
            return result.targets


class MyPipelineStage(Ide.Object, Ide.PipelineStage):
    def do_execute(self, pipeline, cancellable):
        """
        This is a synchronous build stage, which will block the
        main loop. If what you need to do is long running, you
        might consider using do_execute_async() and
        do_execute_finish().
        """
        print("Running my build stage!")

    def do_clean_async(self, pipeline, cancellable, callback, data):
        """
        When the user requests that the build pipeline run the
        clean operation (often before a "rebuild"), this function
        will be executed. Use it to delete stale directories, etc.
        """
        task = Gio.Task.new(self, cancellable, callback)
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

