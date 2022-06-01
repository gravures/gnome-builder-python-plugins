project('gnome-builder-python-plugins',
         version: '0.1.2',
         license: 'GPL-3.0-or-later',
    	 meson_version: '>= 0.55.0',
)

# plugins to install
plugins_list = get_option('plugins')


# Requirements python modules that are required by our plugins
python_requires = {}


# plugin obviously depends on gnome-builder
builder_required_version='3.32'
python_helper = find_program('python_helper', required: true)
printed_version = ''

if get_option('flatpak')
	ret = run_command('flatpak', 'info', 'org.gnome.Builder')
	if ret.stderr() != ''
		error('can not find gnome-builder in flatpak installed applicatons.')
	else
		message('Gnome-builder found in flatpak installed applicatons.')
		printed_version = run_command('flatpak', 'run', 'org.gnome.Builder', '--version').stdout()
	endif
else
	gnome_builder = find_program('gnome-builder', required: true)
	if not gnome_builder.found()
		error('Error: gnome-builder not found')
	else
		message('Gnome-builder path: @0@'.format(gnome_builder.full_path()))
		printed_version = run_command(gnome_builder, '--version').stdout()
	endif
endif

if printed_version == ''
	error('can not obtain gnome-builder version.')
else
	builder_version = printed_version.split()[-1]
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
flatpak = 'flatpak/app/org.gnome.Builder/current/active/files/'
flatpakdir = join_paths(datadir, flatpak)


if get_option('flatpak')
	scriptdir = join_paths(flatpakdir, get_option('bindir'))
	schemas_dir = join_paths(flatpakdir, get_option('datadir'), 'glib-2.0/schemas')
	message('Will install gnome-builder plugins for flatpak...')
	ret = run_command(python_helper, 'venv', flatpakdir)
	if ret.returncode() == 1
		error('Failed to create vrtual env')
	else
		message('Created a virtual env for python requirements testing in flatpak')
	endif
	venv = join_paths(ret.stdout().strip(), 'bin/python')
	flk_msg = ' in flatpak container'
else
	scriptdir = join_paths(prefix, get_option('bindir'))
	schemas_dir = join_paths(datadir, 'glib-2.0/schemas')
	flk_msg = ''
endif


# include
gnome = import('gnome')
message('Will configure those plugin(s): @0@'.format(', '.join(plugins_list)))
subdir('src')


# check python required dependency
foreach key_module, require : python_requires
	desc = key_module.split(':')
	key = desc[0]
	module = desc[1]
	msg = ''
	flk_inst = ':user'

	if key == 'flk' and get_option('flatpak')
		msg = flk_msg
		flk_inst = flatpakdir
		ret = run_command(venv, 'python_helper', 'require', module, require)
	else
		ret = run_command(python_helper, 'require', module, require)
	endif  # end check package

    if ret.returncode() != 0
    	if ret.stdout() == ''
        	msg_out = 'Failed to find required python package @0@@1@'.format(module, msg)
        else
        	msg_out = 'Find python package @0@=@1@@2@, but require version=@3@'.format(module, ret.stdout().strip(), msg, require)
        endif  # end format msg

        if get_option('pip')
        	message(msg_out)
	    	ret = run_command(
	    		python_helper,
	    		'install',
	    		'@0@>=@1@'.format(module, require),
	    		flk_inst
	    	)
	    	if ret.returncode() == 1
	    		message(ret.stderr())
				error('Failed to install @0@@1@'.format(module, msg))
			else
				message(ret.stdout().strip())
				message('package @0@ successfully installed@1@'.format(module, msg))
			endif
		else
		    error(msg_out)
		endif  # end if install
    else
		message(
		    'Found python package @0@=@1@@2@'.format(module, ret.stdout().strip(),
		    msg)
		)
    endif  # end if returncode
endforeach


#
meson.add_install_script('glib-compile-schemas', schemas_dir)


