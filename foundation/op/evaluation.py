
import sys, os
import tqdm

import torch

import omnifig as fig

from ..framework import Recordable, Schedulable, Evaluatable
from .runs import NoOverwriteError
from .. import util

# from .loading import load_config, load_records, setup_logging, setup_records, \
# from .loading import wrap_datasets, wrap_transaction, get_raw_path

from .model import load_model
from .data import load_data


@fig.Script('eval')
def eval_model(A, run=None):
	
	if run is None:
		assert A is not None, 'either run or A must not be None'
		A.push('run._type', 'run', overwrite=False)
		run = A.pull('run')
	
	A = run.get_config()
	
	results = None
	
	try:
		run.prep_eval()
	except NoOverwriteError:
		print('No overwrite, so will exit without doing anything now')
		return 0
	
	model = run.get_model()
	
	print(model)
	print(model.optim)
	if hasattr(model, 'scheduler'):
		print(model.scheduler)
	print('Model has {} parameters'.format(util.count_parameters(model)))
	
	results = run.evaluate()
	
	if results is not None:
		ident = run.eval_identifier
		run.save_results(ident, results)
	
	return A, results, run




