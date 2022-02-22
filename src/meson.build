# global list each plugin will add
# its own dependency
requires = []

# *.plugin ABI confguration
abi_conf = configuration_data()
abi_conf.set('PACKAGE_ABI', abi_version)

# include
foreach plugin : plugins_list
	subdir(plugin)
endforeach

# add dependency to the top level
# python_requires dictionary
foreach pkg : requires
	desc = pkg.split('=')
	module = desc[0]
	version = desc[1]
	defined = python_requires.get(module, 'none')
	if defined != 'none'
		if version.version_compare('>@0@'.format(defined))
			python_requires += {module: version}
		endif
	else
	 	python_requires += {module: version}
	endif
endforeach


