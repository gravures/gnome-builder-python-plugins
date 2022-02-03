conf = configuration_data()
conf.set('abi_version', abi_version)

configure_file(
	input: files('python-setuptools.plugin.in'),
	output: 'python-setuptools.plugin',
	configuration: conf,
	install: true,
	install_dir: plugindir,
)
