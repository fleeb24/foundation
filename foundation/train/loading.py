

import sys,os,time
import numpy as np
import torch

from .. import util

from .config import get_config
# from .data import default_load_data
# from .model import default_create_model



def save_checkpoint(info, save_dir, is_best=False, epoch=None):
	path = None
	if is_best:
		path = os.path.join(save_dir, 'best.pth.tar')
		torch.save(info, path)

	if epoch is not None:
		path = os.path.join(save_dir, 'checkpoint_{}.pth.tar'.format(epoch))
		torch.save(info, path)

	return path

def find_checkpoint(path, load_last=False, saveroot=None):
	if os.path.isfile(path) and '.pth.tar' in path:
		return path

	if saveroot is None and 'FOUNDATION_SAVE_DIR' in os.environ:
		saveroot = os.environ['FOUNDATION_SAVE_DIR']

	if not os.path.isdir(path) and saveroot is not None:
		try:
			long_path = os.path.join(saveroot, path)
			assert os.path.isdir(long_path)
		except AssertionError:
			pass
		else:
			path = long_path

	if os.path.isdir(path):
		if not load_last and 'best.pth.tar' in os.listdir(path):
			pick = 'best.pth.tar'
		else:
			ckpts = [n for n in os.listdir(path) if 'checkpoint' in n and '.pth.tar' in n]
			vals = [int(n.split('_')[-1].split('.')[0]) for n in ckpts]
			if len(vals): # dir exists but no checkpoints
				pick = 'checkpoint_{}.pth.tar'.format(max(vals))
				print('Found {} checkpoints. Using {}'.format(len(ckpts), pick))
			elif 'config.tml' in os.listdir(path):
				print('Found 0 checkpoints. However, a config file was found')
				return path
		path = os.path.join(path, pick)

		return path

	raise FileNotFoundError('Invalid path: {}'.format(path))



def load(path=None, A=None, get_model=None, get_data=None, mode='train',
         load_state_dict=True, load_last=False, return_args=True, return_ckpt=False):
	assert path is not None or A is not None, 'must provide either path to checkpoint or args'
	assert get_model is not None or get_data is not None, 'nothing to load'

	# if get_model is 'default':
	# 	get_model = default_create_model
	# if get_data is 'default':
	# 	get_data = default_load_data

	checkpoint = None
	if path is not None:
		ckptpath = find_checkpoint(path, load_last=load_last)

		if os.path.isfile(ckptpath):
			checkpoint = torch.load(ckptpath)
			config_dir = os.path.dirname(ckptpath)
		else:
			config_dir = ckptpath
		load_A = get_config(os.path.join(config_dir, 'config.tml'))
		if A is None:
			A = load_A
		else:
			new_A = A.copy()
			A.clear()
			A.update(load_A)
			A.update(new_A)
		print('Loaded {}'.format(ckptpath))

	out = []

	if return_args:
		out.append(A)

	if get_data is not None:
		util.set_seed(A.seed)

		if checkpoint is not None and 'datasets' in checkpoint:
			datasets = checkpoint['datasets']
		else:
			datasets = get_data(A, mode=mode)

		out.append(datasets)

	if get_model is not None:
		util.set_seed(A.seed)

		model = get_model(A)

		model.to(A.device)

		if checkpoint is not None and 'model_state' in checkpoint and load_state_dict:
			model.load_state_dict(checkpoint['model_state'])
			print('Loaded model_state from checkpoint')

		out.append(model)

	if return_ckpt:
		out.append(checkpoint)

	return out

