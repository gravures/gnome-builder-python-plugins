# Requirements
requires += ['flk:isort=5.0']

# sub directory instalation
plugindir = 'python-isort'

# sources files
py_src = ['python_isort_plugin.py',
	  'isort_preferences.py']

configure_file(
	input: files('python_isort.plugin.in'),
	output: 'python_isort.plugin',
	configuration: abi_conf,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)

gnome.compile_resources(
  	'python_isort_plugin',
  	'python_isort.gresource.xml',
  	gresource_bundle: true,
	install: true,
       	install_dir: join_paths(builder_plugindir, plugindir),
)

custom_target(
	'python_isort',
	command: ['cp', '@INPUT@', '@OUTDIR@'],
	input: files(py_src),
	output: py_src,
	build_always: true,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)

install_data(
	'org.gnome.builder.plugins.python-isort.gschema.xml',
  	install_dir: schemas_dir
)

