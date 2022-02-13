from setuptools import setup

setup(
   name='ngsim',
   version='0.1',
   description='Module for simulation around ngspice',
   author='Christoph Weiser',
   packages=['ngsim'],
   install_requires=['numpy', 'pandas', 'matplotlib']
)
