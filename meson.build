project('gnome-builder-setuptools-plugin',
         version: '0.1.0',
         license: 'GPL-3.0-or-later',
    	 meson_version: '>= 0.50.0',
)


# plugin obviously depends on gnome-builder
gnome_builder = find_program('gnome-builder', required: true)
builder_required_version='3.38'

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


# external python modules that are required by our plugin
python_modules = ['build']

# instalation paths
prefix = get_option('prefix')
datadir = join_paths(prefix, get_option('datadir'))
plugindir = join_paths(datadir, 'gnome-builder/plugins/python-setuptools-plugin')

# check python required dependency
pymod = import('python')
if meson.version().version_compare('>=0.51')
    py3 = pymod.find_installation(modules: python_modules)
else
    py3 = pymod.find_installation()
endif
foreach module: python_modules
    if run_command(py3, '-c', 'import @0@'.format(module)).returncode() != 0
        error('Failed to find required python module \'@0@\'.'.format(module))
	else
		message('Founded python module \'@0@\'.'.format(module))
    endif
endforeach

subdir('src')

# install
install_subdir(
	'src',
	install_dir: plugindir,
	exclude_files: ['python-setuptools.plugin.in', 'meson.build'],
	strip_directory: true,
)





