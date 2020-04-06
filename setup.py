from setuptools import setup

setup(name='foundation',
      version='0.2',
      description='Framework for RL and beyond',
      url='https://gitlab.cs.washington.edu/fleeb/foundation',
      author='Felix Leeb',
      author_email='fleeb@uw.edu',
      license='MIT',
      packages=['foundation'],
      install_requires=[
            'numpy',
            'matplotlib',
            'torch',
            # 'tensorflow',
            'gym',
            'OpenCV-Python',
            'tabulate',
            'configargparse',
            'ipdb',
            'h5py',
            'pyyaml',
            'tqdm',
            'pandas',
      ],
      zip_safe=False)
