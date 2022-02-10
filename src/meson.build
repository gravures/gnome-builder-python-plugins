conf = configuration_data()
conf.set('PACKAGE_ABI', abi_version)

configure_file(
	input: files('python_517_build.plugin.in'),
	output: 'python_517_build.plugin',
	configuration: conf,
	install: true,
	install_dir: plugindir,
)
