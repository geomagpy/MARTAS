git tag -a 1.0.0 -m 'version 1.0.0'
vers=`git describe master`
line="__version__ = '$vers'"
echo $line > /home/leon/Software/MARTAS/doc/version.py
