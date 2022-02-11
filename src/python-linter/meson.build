conf = configuration_data()
conf.set('PACKAGE_ABI', abi_version)

# Requirements
requires += ['pylint=2.12']

plugindir = 'python-linter'

py_src = ['python_linter_plugin.py']

configure_file(
	input: files('python_linter.plugin.in'),
	output: 'python_linter.plugin',
	configuration: conf,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)

custom_target(
	'python_linter',
	command: ['cp', '@INPUT@', '@OUTDIR@'],
	input: files(py_src),
	output: py_src,
	build_always: true,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)

install_data(
	'org.gnome.builder.plugins.python-linter.gschema.xml',
  	install_dir: schemas_dir
)

