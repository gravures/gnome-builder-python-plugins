# Requirements
requires += ['setuptools=52.0',
             'build=0.1.0',
             'pip=20.3',
             'tomli=1.2',
             'packaging=20.9']

# sources files
py_src = ['python_517_build_plugin.py',
	 'backends.py',
	 'stage.py']

# sub directory installation
plugindir = 'python-517-build'

configure_file(
	input: files('python_517_build.plugin.in'),
	output: 'python_517_build.plugin',
	configuration: abi_conf,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)

custom_target(
	'python_517',
	command: ['cp', '@INPUT@', '@OUTDIR@'],
	input: files(py_src),
	output: py_src,
	build_always: true,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)
