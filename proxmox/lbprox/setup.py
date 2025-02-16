from setuptools import setup

__version__ = "0.1.0"

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='lbprox',
    version=__version__,
    install_requires=requirements,
    packages=['lbprox',
              'lbprox/ssh',
              'lbprox/allocations',
              'lbprox/flavors',
              'lbprox/cli',
              'lbprox/common',
              'lbprox/deployment',
              'lbprox/snippets',
              'lbprox/dashboard',
              'lbprox/cli/allocations',
              'lbprox/cli/data_network',
              'lbprox/cli/image_store',
              'lbprox/cli/os_images',
              'lbprox/cli/dashboard',
              'lbprox/cli/prom_discovery',
              'lbprox/cli/nodes'
    ],          
    entry_points={
        'console_scripts': [
            'lbprox = lbprox.main:main'
        ]
    }
)
