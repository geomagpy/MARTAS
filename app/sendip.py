import subprocess
from magpy.transfer import *
import magpy.opt.cred as mpcred

ippath = '/home/cobs/MARTAS/Logs/ip.txt'

last = open(ippath,'r')
lastip = last.read()
last.close()

#sendcmd = 'ifconfig > ' + ippath
sendcmd = 'wget -qO- http://ipecho.net/plain > ' + ippath
subprocess.call(sendcmd,shell=True)

cred = 'zamg'
sendpath = '/data/station1'

address=mpcred.lc(cred,'address')
user=mpcred.lc(cred,'user')
passwd=mpcred.lc(cred,'passwd')
port=21
pathtolog = '/tmp/magpytransfer.log'

current = open(ippath,'r')
currentip = current.read()
current.close()

if currentip != lastip:
    print "IP has changed. Sending..."
    ftpdatatransfer(localfile=ippath,ftppath=sendpath,myproxy=address,port=port,login=user,passwd=passwd,logfile=pathtolog,raiseerror=True)
else:
    print "IP is the same. Doing nothing."


