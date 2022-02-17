# Requirements
requires += ['pylint=2.12']

# sub directory installation
plugindir = 'python-linter'

# sources files
py_src = ['python_linter_plugin.py',
	  'linters.py',
	  'preferences.py',
	  'preferences_entry.py',
	  'preferences_entry.ui']

configure_file(
	input: files('python_linter.plugin.in'),
	output: 'python_linter.plugin',
	configuration: abi_conf,
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

