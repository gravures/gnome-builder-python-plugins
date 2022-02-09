project('gnome-builder-setuptools-plugin',
         version: '0.1.0',
         license: 'GPL-3.0-or-later',
    	 meson_version: '>= 0.50.0',
)


# Requirements
# external python modules that are required by our plugin
builder_required_version='3.32'
python_modules = ['setuptools=52.0',
                  'build=0.1.0',
                  'pip=20.3',
                  'tomli=1.2',
                  'packaging=20.9']

# plugin obviously depends on gnome-builder
gnome_builder = find_program('gnome-builder', required: true)

if not gnome_builder.found()
	error('Error: gnome-builder not found')
else
	ret = run_command(gnome_builder, '--version')
	if ret.stdout() == ''
		error('can not obtain gnome-builder version.')
	endif
	builder_version = ret.stdout().split().get(2)
	if builder_version.version_compare('<' + builder_required_version)
        error('need at least version 3.38 of gnome-builder\ninstalled version=@0@'.format(builder_version))
    else
    	message('gnome-builder version=@0@'.format(builder_version))
    endif
    version_parts = builder_version.split('.')
    abi_version = '@0@.@1@'.format(version_parts[0], version_parts[1])
endif


# instalation paths
prefix = get_option('prefix')
datadir = join_paths(prefix, get_option('datadir'))
plugindir = join_paths(datadir, 'gnome-builder/plugins/python_517_build_plugin')

# check python required dependency
foreach module_desc: python_modules
	module_desc = module_desc.split('=')
	module = module_desc[0]
	require = module_desc[1]
	ret = run_command(files('check_python_dep'), module, require)
    if ret.returncode() != 0
    	if ret.stderr() == ''
        	error('Failed to find required python module @0@'.format(module))
        else
        	error('Find python module @0@=@1@, but require version=@2@'.format(module, ret.stderr(), require))
        endif
	else
		message('Founded python module @0@=@1@'.format(module, ret.stdout()))
    endif
endforeach

subdir('src')

# install
install_subdir(
	'src',
	install_dir: plugindir,
	exclude_files: ['python_517_build.plugin.in', 'meson.build'],
	strip_directory: true,
)





