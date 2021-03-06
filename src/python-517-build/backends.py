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
from enum import Enum


class BuildType(Enum):
    SDIST = 0
    WHEEL = 1
    EGG = 2
    FILE = 3
    TREE = 4


class Python517BuildBackend(ABC):
    # TODO: c extension build_ext

    def get_name(self):
        """Return the canonic name of the backend."""
        return self.__name__

    @abstractmethod
    def get_display_name(self):
        """Return a string to show in the ui."""
        pass

    @abstractmethod
    def get_build_types(self):
        """Return the type of build produced by this Backend.

        Returns(BuildType): return type as a member of BuildType
                            enumeration.
        """
        pass

    @abstractmethod
    def get_builddir_name(self):
        """Get the name of the build directory.

        Returns(str): name of directory.
        """
        return "dist"

    def get_builddir(self, root_dir):
        """A method returning the path used as the build directory
        for this Backend.

        Args:
            root_dir(Gio.File): the root directory for the project.

        Returns(Gio.File): the build directory path for this Backend.
        """
        return root_dir.get_child(self.get_builddir_name())

    @abstractmethod
    def get_build_cmd(self):
        """Gets the arguments used to build a sdist.

        Returns(list): a list containing the arguments to run.
        """
        pass

    @abstractmethod
    def get_wheel_cmd(self):
        """Gets the arguments used to build a wheel.

        Returns(list): a list containing the arguments to run.
        """
        pass

    def get_clean_cmd(self):
        """Gets the arguments used to clean the builds.

        Returns(list): a list containing the arguments to run or None.
        """
        return

    @abstractmethod
    def has_isolation(self):
        """Is this build Backend run natively in a virtual env.

        Returns(bool): True if Backend has isolation.
        """
        pass


class PypaBuildBackend(Python517BuildBackend):
    """PypaBuildBackend. """

    def get_display_name(self):
        return "Pypa Build"

    def get_build_types(self):
        return [BuildType.SDIST]

    def get_builddir_name(self):
        return "dist"

    def get_build_cmd(self):
        return ["python",
                "-m",
                "build",
                "--sdist",
                "--outdir",
                self.get_builddir_name()]

    def get_wheel_cmd(self):
        return ["python",
                "-m",
                "build",
                "--outdir",
                self.get_builddir_name()]

    def has_isolation(self):
        return True
