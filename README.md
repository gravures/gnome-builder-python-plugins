# gnome-builder python plugins

## About

A set of **gnome-builder** extensions for Python development.

* **python-517** (a pep-517 build system)

* **python-linter** (integration of flake8 and pylint)

* **python-isort** (sort import statements)

* **python-symbol** (meaningfull symbol tree view)

After installation a new page in the preferences panel will be available with sections for the different plugins.

##### global requirements:

- gnome-builder >= 3.32
- Python >=3.6

## Installing

This project uses the [meson build system](http://mesonbuild.com/). Run the following commands to clone this project and initialize the build:

```
$ git clone https://github.com/gravure-dtp/gnome-builder-python-plugins.git
$ cd gnome-builder-python-plugins
$ meson build --prefix=~/.local
```

Note: `build` is the build output directory and can be changed to any other
directory name.

To build or re-build after code-changes, run:

```
$ meson --reconfigure --prefix=~/.local build
```

To install, run:

```
$ meson compile -C build
$ meson install -C build
```

## Install only specific plugins

You can specify with the -Dplugins configure option a list of plugin(s) to install:

```
$ meson build --prefix=~/.local -Dplugins=python-linter,python-517-build
```

## Flatpak specific installation

To install plugins for your gnome-builder flatpak's distribution use the -Dflatpak option:

```
$ meson build --prefix=~/.local -Dflatpak=true
$ meson compile -C build
$ meson install -C build
```

Note: this will only install certains files to the flatpak container (because thoses files can't be share with user space)

You will need to install some python packages in the flatpak container, currently those packages will be *packaging* and *tomli* for the python-517 plugin.

To show Python installed packages in your gnome-builder flatpak's distribution:

```
$ pip freeze --path ~/.local/share/flatpak/app/org.gnome.Builder/current/active/files/lib/python3.9/site-packages
```

To install or upgrade a specific Python requirement to your gnome-builder flatpak's distribution:

```
pip install packaging>=20.9 --upgrade -t ~/.local/share/flatpak/app/org.gnome.Builder/current/active/files/lib/python3.9/site-packages
```

Note: pip does not permit to uninstall package in a custom directory, if you want to remove thoses packages you should do it manually. 

## python-517 plugin

Provide a modern python build system defined through the [PEP 517](https://www.python.org/dev/peps/pep-0517/#build-requirements) (a build-system independent format for source trees). This is also well known as the [pyproject.toml](https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/) interface.
Currently the only supported build backend is the **Pypa** [build](https://pypa-build.readthedocs.io/en/latest/) backend.

##### plugin requirements:

- setuptools >= 42.0
- build >= 0.1.0
- pip >= 20.3
- *packaging* >= 20.9
- *tomli* >= 1.2

## python-linter plugin

Provide integration with [PyLint](https://pylint.org/) and [Flake8](https://flake8.pycqa.org/en/latest/index.html) Python linters.

##### plugin requirements:

* pylint >= 2.12
* *or* flake8

None of those linter requirements are mandatory, the plugin will check at runtime witch linter is available. You can select the linter to use in the preferences window. You can even install a new linter when builder is running (you have to close and open again the preferences window to show the new linter). For flatpack you don't have to install any linter in the gnome-builder container, instead just install as usual:

```
$ pip install flake8 --user
```

## python-isort plugin

[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

Add an entry in the source view menu to sort import statements with [isort](https://pycqa.github.io/isort/index.html).

##### plugin requirements:

- isort >= 5.0

For flatpack you don't have to install isort in the gnome-builder container, instead just install as usual.

## python-symbols plugin

Give to gnome-builder editor a meaningfull symbol code tree view.  Symbols shown in the list view can be adjusted in preferences panel (show imported modules, show variables at modules level or at class level).

## License

**gnome-builder python plugins** are free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.
