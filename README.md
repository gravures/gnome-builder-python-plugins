# gnome-builder setuptools plugin

## About

A gnome-builder extension adding a setuptool build target.


## Features

## Requirements

* gnome-builder >= 3.38
* Python >=3.6
* Pypa setuptools >= 42.0
* Pypa build


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
$ meson --reconfigure
```

To install, run:

```
$ cd build && meson install
```


## License

'gnome-builder setuptools plugin' is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

