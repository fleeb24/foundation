
import sys, os, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from .. import util
from torch.utils.data import TensorDataset, DataLoader, ConcatDataset
from ..data.collectors import *

def simple_split_dataset(dataset, split, shuffle=True):
	'''

	:param dataset:
	:param split: split percent as ratio [0,1]
	:param shuffle:
	:return:
	'''

	assert 0 < split < 1

	if shuffle:
		dataset = Shuffle_Dataset(dataset)

	ncut = int(len(dataset) * split)

	part1 = Subset_Dataset(dataset, np.arange(0,ncut))
	part2 = Subset_Dataset(dataset, np.arange(ncut, len(dataset)))

	return part1, part2

def split_dataset(dataset, split1, split2=None, shuffle=True):
	p1, p2 = simple_split_dataset(dataset, split1, shuffle=shuffle)
	if split2 is None:
		return p1, p2
	split2 = split2 / (1 - split1)
	p2, p3 = simple_split_dataset(p2, split2, shuffle=False)
	return p1, p2, p3

def load_data(path=None, args=None):

	datasets = _load_data(path=path, args=args)

	if not hasattr(args, 'def_device'):
		args.def_device = None

	# formatting for all datatsets here
	datasets = [Movable_Dataset(ds, device=args.def_device) for ds in datasets]


	return datasets

def _load_data(path=None, args=None):
	assert path is not None or args is not None, 'must specify the model'

	if path is not None:
		if os.path.isdir(path):
			path = os.path.join(path, 'best.pth.tar')
		assert os.path.isfile(path), 'Could not find encoder:' + path

		checkpoint = torch.load(path)

		if 'traindata' in checkpoint and 'testdata' in checkpoint:
			print('Loaded dataset from {}'.format(path))
			if 'valdata' in checkpoint:
				return checkpoint['traindata'], checkpoint['valdata'], checkpoint['testdata']
			return checkpoint['traindata'], checkpoint['testdata']

		print('Loaded args from {}'.format(path))
		args = checkpoint['args']

	if args.dataset == 'mnist':

		args.save_datasets = False

		args.din = 1, 28, 28

		traindata = torchvision.datasets.MNIST('data/mnist/', train=True, download=True,
											   transform=torchvision.transforms.ToTensor())
		testdata = torchvision.datasets.MNIST('data/mnist/', train=False, download=True,
											  transform=torchvision.transforms.ToTensor())

		if hasattr(args, 'indexed') and args.indexed:
			traindata = Indexed_Dataset(traindata)
			testdata = Indexed_Dataset(testdata)

		if args.use_val:

			traindata, valdata = split_dataset(traindata, split=args.val_per, shuffle=False)
			
			return traindata, valdata, testdata
		
		return traindata, testdata

	if 'hf' in args.dataset:

		args.save_datasets = True

		n = len(args.data)

		args.data_files = []

		# print('Removing half of the ambient data')
		for dd in args.data:
			new_files = [os.path.join(dd, df) for df in os.listdir(dd)]

			num = len(new_files)

			new_files = new_files#[:num // n]

			print('Found {} samples in {} using {}'.format(num, dd, len(new_files)))

			args.data_files.extend(new_files)

		fmt_fn = None
		if 'seq' in args.dataset:

			dataset = ConcatDataset([H5_Flattened_Dataset(d, keys={'rgbs'}) for d in args.data_files])
			fmt_fn = format_h5_seq

		else:
			dataset = ConcatDataset([H5_Dataset(d, keys={'rgbs'}) for d in args.data_files])

			assert False

		datasets = split_dataset(dataset, args.test_per)

		if args.use_val:

			valdata, traindata = split_dataset(datasets[-1], args.val_per, shuffle=False)

			datasets = datasets[0], valdata, traindata

		datasets = [Format_Dataset(ds, format_fn=fmt_fn) for ds in datasets]

		return datasets[::-1]


	# Failed
	raise Exception('Unknown dataset: {}'.format(args.dataset))


def format_h5_seq(raw):

	x = torch.from_numpy(util.str_to_rgb(raw['rgbs'])).permute(2,0,1).float() / 255

	return x,



