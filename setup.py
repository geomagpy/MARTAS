try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import sys
import shutil
exec(open('martas/version.py').read())
shutil.copyfile('martas/acquisition.py','scripts/acquisition')
shutil.copyfile('martas/collector.py','scripts/collector')
shutil.copyfile('martas/martas_init.py', 'scripts/martas_init')

install_requires=[
            "geomagpy > 1.1.9",
            "numpy >= 1.21.0",
            "scipy >= 1.7.1",
            "paramiko",
            "pexpect",
            "pyserial",
            "requests",
            "python-crontab",
            "twisted",
            "plotly",
            "dash",
            "dash_daq",
            "twisted",
            "setuptools >= 61.0.0"
          ]

setup(
    name='martas',
    version=__version__,
    author='R. Leonhardt, R. Bailey, R. Mandl',
    author_email='roman.leonhardt@geosphere.at',
    packages=['martas', 'martas.app', 'martas.conf', 'martas.core', 'martas.doc', 'martas.init', 'martas.lib', 'martas.logrotate', 'martas.scripts', 'martas.telegram', 'martas.web', 'martas.web.assets'],
    scripts=['scripts/collector','scripts/acquisition', 'scripts/martas_init'],
    url='',
    license='LICENSE.txt',
    description='MARTAS',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    package_data={'martas': ['conf/*.cfg', 'doc/*.pdf', 'doc/*.md', 'init/*.sh', 'init/*.json', 'install/*.sh', 'logrotate/*.logrotate', 'scripts/*.sh', 'web/*.js', 'web/*.html', 'web/*.py', 'web/assets/*']  },
    install_requires=install_requires,
)
