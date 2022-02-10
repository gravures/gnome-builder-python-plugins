# gnome-builder pep 517 plugin

## About

A gnome-builder extension adding a setuptools build target.


## Features

Provide a modern python build system defined through the [pyproject.toml](https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/) interface.
Currently the only supported build backend is the Pypa [build](https://pypa-build.readthedocs.io/en/latest/) backend.

## Requirements

* gnome-builder >= 3.32
* Python >=3.6
* setuptools >= 42.0
* build >= 0.1.0
* pip >= 20.3
* packaging >= 20.9
* tomli >= 1.2


## Installing

This plugin uses the [meson build system](http://mesonbuild.com/). Run the following
commands to clone this project and initialize the build:

```
$ git clone https://github.com/gravure-dtp/gnome-builder-setuptools-plugin.git
$ cd gnome-builder-setuptools-plugin
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
$ meson install -C build
```

## Flatpak installation

To show installed packages in your gnome-builder flatpak's distribution:

```
$ pip freeze --path ~/.local/share/flatpak/app/org.gnome.Builder/current/active/files/lib/python3.9/site-packages
```

To install or upgrade a requirement in your gnome-builder flatpak's distribution:

```
pip install packaging>=20.9 --upgrade -t ~/.local/share/flatpak/app/org.gnome.Builder/current/active/files/lib/python3.9/site-packages
```



## License

'gnome-builder pep 517 plugin' is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

