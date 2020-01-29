
import os
import inspect
import torch
from torch import nn

from .. import util
from .. import framework as fm


_config_registry = {}
def register_config(name, path):
	assert os.path.isfile(path), 'Cant find config file: {}'.format(path)
	_config_registry[name] = path
def register_config_dir(path, recursive=False, prefix=None, joiner=''):
	assert os.path.isdir(path)
	for fname in os.listdir(path):
		parts = fname.split('.')
		candidate = os.path.join(path, fname)
		if os.path.isfile(candidate) and len(parts) > 1 and parts[-1] in {'yml', 'yaml'}:
			name = parts[0]
			if prefix is not None:
				name = joiner.join([prefix, name])
			register_config(name, os.path.join(path, fname))
		elif recursive and os.path.isdir(candidate):
			newprefix = fname if prefix is None else os.path.join(prefix, fname)
			register_config_dir(candidate, recursive=recursive, prefix=newprefix, joiner=os.sep)

def view_config_registry():
	return _config_registry.copy()

def find_config_path(name):
	if os.path.isfile(name):
		return name

	if name in _config_registry:
		return _config_registry[name]
	elif 'FOUNDATION_SAVE_DIR' in os.environ:

		run_dir = name if os.path.isdir(name) else os.path.dirname(name) # full path to run dir or ckpt
		path = os.path.join(run_dir, 'config.yml')

		if not os.path.isfile(path) and 'FOUNDATION_SAVE_DIR' in os.environ:  # path (using default save dir) to run dir or ckpt

			path = os.path.join(os.environ['FOUNDATION_SAVE_DIR'], name)
			run_dir = path if os.path.isdir(path) else os.path.dirname(path)

			path = os.path.join(run_dir, 'config.yml') # run dir

		name = path

	assert os.path.isfile(name), 'invalid path: {}'.format(name)
	return name

_component_registry = {}
_reserved_names = set() #{'list'}
def register_component(name, create_fn):
	'''
	create_fn takes a single input - a Config object
	The config object is guaranteed to have at least one entry with key "_type" and the value is the same as
	the registered name of the component.

	:param name: str (should be unique to this component)
	:param create_fn: callable accepting one arg (a Config object) (these should usually be classes)
	'''
	assert name not in _reserved_names, '{} is reserved'.format(name)
	if name in _component_registry:
		print('WARNING: A component with name {} was already registered'.format(name))
	_component_registry[name] = create_fn

def view_component_registry():
	return _component_registry.copy()

_appendable_keys = {'_mod'} # mods can be appended when updating (instead of overwriting)
# def register_appendable_key(key): # At that point, they might as well manipulate _appendable_keys directly
# 	_appendable_keys.add(key)

_mod_registry = {}
def register_modifier(name, mod_fn, expects_config=False):
	'''
	Takes as input the "create_fn" of some component and a Config object.

	NOTE: modifier names may not start with "+", as that is used to signify that the mod should be
	appended when merging configs

	:param name: str (should be unique to this component, may not start with "+")
	:param mod_fn: callable accepting one arg (the "create_fn" of a registered component)
	(these should usually be classes)
	'''
	assert name not in _reserved_names, '{} is reserved'.format(name)
	_mod_registry[name] = mod_fn, expects_config

def view_modifier_registry():
	return _mod_registry.copy()

def Modifier(name=None, expects_config=False):
	'''
	Decorator to register a modifier

	NOTE: modifiers are usually not types/classes, but functions

	:param name: if not provided, will use the __name__ attribute.
	:param expects_config: True iff this modifier expects to be given the config as second arg
	:return: decorator function
	'''
	def _mod(mod):
		nonlocal name, expects_config
		if name is None:
			name = mod.__name__
		register_modifier(name, mod, expects_config=expects_config)
		return mod
	return _mod

def AutoModifier(name=None):
	'''
	Can be used to automatically register modifiers that combine types

	To keep component creation as clean as possible, modifier types should allow arguments to their __init__
	(other than the Config object) and only call pull on arguments not provided, that way child classes of
	the modifier types can specify defaults for the modifications without calling pull() multiple times
	on the same arg.

	(eg. see `Cropped` in .datasets.transforms)

	Note: in a way, this converts components to modifiers (but think before using). This turns the modified
	component into a child class of this modifier and its previous type.

	In short, Modifiers are used for wrapping of components, AutoModifiers are used for subclassing components

	:param name: if not provided, will use the __name__ attribute.
	:return: decorator to decorate a function
	'''

	def _auto_mod(mod_type):
		nonlocal name
		def _the_mod(cmpn_type):
			# awesome python feature -> dynamic type declaration!
			return type('{}_{}'.format(mod_type.__name__, cmpn_type.__name__), (mod_type, cmpn_type), {})
		Modifier(name=name)(_the_mod)
		return mod_type

	return _auto_mod


def Component(name=None):
	'''
	Decorator to register a component

	NOTE: components should usually be types/classes to allow modifications

	:param name: if not provided, will use the __name__ attribute.
	:return: decorator function
	'''
	def _cmp(cmp):
		nonlocal name
		if name is None:
			name = cmp.__name__
		register_component(name, cmp)
		return cmp
	return _cmp

class MissingConfigError(Exception): # TODO: move to a file containing all custom exceptions
	def __init__(self, key):
		super().__init__(key)

def create_component(info):
	'''
	Creates the component specified in info (checks component registry using info.pull('_type'),
	and modifier registry for info.pull('_mod'))

	_mod can be a list, inwhich case they will be applied in the given order, eg:

	let mods = [A, B, C]

	component <- C(B(A(component)))

	NOTE: generally, start with more specific modifications, and become more general

	:param info: should be a Config object with attribute "_type" (and optionally "_mod")
	:return: component(info)
	'''

	name = info.pull('_type', silent=True)

	assert name in _component_registry, 'Unknown component type (have you registered it?): {}'.format(name)

	component = _component_registry[name]

	try:
		mod_names = info.pull('_mod', silent=True)
	except MissingConfigError:
		mod_names = None

	if mod_names is not None:

		if not isinstance(mod_names, (list, tuple)):
			mod_names = mod_names,

		for mod_name in mod_names: # WARNING: apply modifications in reverse order
			if mod_name[0] == '+': # filter out initial + if found
				mod_name = mod_name[1:]
			mod, expects_config = _mod_registry[mod_name]
			component = mod(component, info) if expects_config else mod(component)

	return component(info)



