project('gnome-builder-pep517-plugin',
         version: '0.1.0',
         license: 'GPL-3.0-or-later',
    	 meson_version: '>= 0.53.0',
)


# Requirements python modules that are required by our plugins
python_requires = {}


# plugin obviously depends on gnome-builder
builder_required_version='3.32'
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
endif


# Compute ABI Version from gnome-builder version
version_parts = builder_version.split('.')
abi_major = version_parts[0]
if abi_major.to_int() < 40
	abi_minor = version_parts[1]
else
	abi_minor = 0
endif
abi_version = '@0@.@1@'.format(abi_major, abi_minor)
message('Configure build for ABI version @0@'.format(abi_version))


# installation paths
prefix = get_option('prefix')
datadir = join_paths(prefix, get_option('datadir'))
builder_plugindir = join_paths(datadir, 'gnome-builder/plugins')
schemas_dir = join_paths(datadir, 'glib-2.0/schemas')


# include
subdir('src')


# check python required dependency
foreach module, require : python_requires
	ret = run_command(files('check_python_dep'), module, require)
    if ret.returncode() != 0
    	if ret.stderr() == ''
        	error('Failed to find required python module @0@'.format(module))
        else
        	error('Find python module @0@=@1@, but require version=@2@'.format(module, ret.stderr(), require))
        endif
	else
		message('Founded python module @0@=@1@'.format(module, ret.stdout().strip()))
    endif
endforeach


#
meson.add_install_script('glib-compile-schemas', schemas_dir)







