# gnome-builder setuptools plugin

## About

A gnome-builder extension adding a setuptool build target.


## Features

Provide a modern python build system defined throught the [pyproject.toml](https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/) interface.
Currently the only supported build backend is the Pypa [build](https://pypa-build.readthedocs.io/en/latest/) backend.

## Requirements

* gnome-builder >= 3.32
* Python >=3.6
* setuptools >= 42.0
* build >= 0.1.0
* pip >= 20.3


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


## License

'gnome-builder setuptools plugin' is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

