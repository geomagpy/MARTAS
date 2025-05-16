try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys
import shutil
exec(open('doc/version.py').read())
shutil.copyfile('collector.py','scripts/collector')
shutil.copyfile('acquisition.py','scripts/acquisition')

install_requires=[
            "geomagpy > 1.1.9",
            "numpy >= 1.21.0",
            "scipy >= 1.7.3",
            "pyserial",
            "twisted",
            "setuptools"
          ]

setup(
    name='martas',
    version=__version__,
    author='R. Leonhardt',
    author_email='roman.leonhardt@geosphere.at',
    packages=['app', 'conf', 'core', 'doc', 'init', 'install', 'libmqtt', 'telegram', 'web'],
    scripts=['scripts/collector','scripts/acquisition', 'scripts/martas_init', 'scripts/marcos_init'],
    url='',
    license='LICENSE.txt',
    description='MARTAS',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    package_data={'conf': ['*.cfg'], 'doc': ['*.pdf', '*.md'], 'init': ['*.sh', '*.json'], 'install': ['*.sh'], 'web': ['*.js', '*.html']  },
    install_requires=install_requires,
)
