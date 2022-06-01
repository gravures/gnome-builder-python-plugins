# Requirements
requires += ['flk:parso=0.8.1']

# sub directory installation
plugindir = 'python-symbols'

# sources files
py_src = ['python_symbols_plugin.py',
		  'parsers.py',
     	  'symbols_preferences.py']

configure_file(
	input: files('python_symbols.plugin.in'),
	output: 'python_symbols.plugin',
	configuration: abi_conf,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)

custom_target(
	'python_symbols',
	command: ['cp', '@INPUT@', '@OUTDIR@'],
	input: files(py_src),
	output: py_src,
	build_always: true,
	install: true,
	install_dir: join_paths(builder_plugindir, plugindir),
)

install_data(
 	'sources_inspect.py',
   	install_dir: scriptdir,
   	install_mode: 'rwxr-xr-x'
)

install_data(
	'org.gnome.builder.plugins.python-symbols.gschema.xml',
  	install_dir: schemas_dir
)


