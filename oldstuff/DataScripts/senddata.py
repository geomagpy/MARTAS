#!/usr/bin/python

"""
Send data from MARTAS to any other machine using cron/scheduler:
senddata.py needs to options 
-c to define the credentials, address and type of the transfer protocol
-p path to data
-d (optional) depths (1 until yesterday, 2 day before yesterday, 3....)
-i incremental given in minutes e.g. "10" only send the last 10 minutes. overwrites -d
Description:
senddata will deliver datasets within the given path (by default the last and current day) to the
tranfer adress, maintaining the directory structure.
If failing, an log infomation is established and data transfer will be retried at the next croned
time.
"""

import sys, getopt, zipfile
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED
try:
    from magpy.stream import *
    from magpy.transfer import *
    from magpy.opt import cred as mpcred
except:
    sys.path.append('/home/leon/Software/magpy/trunk/src')
    from stream import *
    from transfer import *
    from opt import cred as mpcred


def main(argv):
    cred = ''
    path = ''
    remotepath = ''
    protocol = ''
    depth = 2
    increment = False
    extension = 'bin'
    dateformat = '%Y-%m-%d'
    compress = False
    try:
        opts, args = getopt.getopt(argv,"hc:l:r:s:d:i:e:f:z",["cred=","localpath=","remotepath=","protocol=","depth=","increment=","extension=","dateformat=",])
    except getopt.GetoptError:
        print 'senddata.py -c <credentialshortcut> -s <protocol> -l <localpath> -r <remotepath> -d <depth> -i <increment> -e <extension> -f <dateformat> -z'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print '-------------------------------------'
            print 'Description:'
            print 'Sending data to a remote host by scp or ftp.'
            print 'Requires existing credential information (see cred.py).'
            print '-------------------------------------'
            print 'Usage:'
            print 'senddata.py -c <credentialshortcut> -l <localpath> -r <remotepath> '
            print '  -s <protocol> -d <depth> -i <increment> -e <extension> -f <dateformat>'
            print '-------------------------------------'
            print 'Options:'
            print '-c (required): the credentials for the transfer protocol.'
            print '               Create using the addcred.py method. Use'
            print '               python addred.py -h for help on that.'
            print '-l (required): provide a local root path, all directories below will'
            print '               be scanned for *date.bin files'
            print '-r           : eventually provide a remote path like "/data"' 
            print '-s (required): provide the protocol to be used (ftp or scp)'
            print '-d           : defines the amount of days to be send: 1 for today only,'
            print '               2 for the last two days and so on. d needs to be a integer'
            print '               with d > 1.'
            print '-i (experimental): defines incremental uploads. Loaded data is extracted by Magpy'
            print '               and i minutes are uploaded and appended to an existing file.'
            print '               This file needs to be unified later on.'
            print '-e           : provide a user defined extension, default is "bin"'
            print '-f           : provide a date format, default is "%Y-%m-%d"'
            print '-z           : compress file before sending'
            print '-------------------------------------'
            print 'Examples:'
            print 'python senddata.py -c zamg -s ftp -l /srv/ws/ -r /data'

            sys.exit()
        elif opt in ("-c", "--cred"):
            cred = arg
        elif opt in ("-l", "--localpath"):
            path = arg
        elif opt in ("-r", "--remotepath"):
            remotepath = arg
        elif opt in ("-s", "--protocol"):
            protocol = arg
        elif opt in ("-d", "--depth"):
            try:
                depth = int(arg)
                if not depth >= 1:
                    print "depth needs to be positve" 
                    sys.exit()
            except:
                print "depth needs to be an integer" 
                sys.exit()
        elif opt in ("-i", "--increment"):
            increment = arg
        elif opt in ("-e", "--extension"):
            extension = arg.strip('.')
        elif opt in ("-f", "--dateformat"):
            dateformat = arg
        elif opt in ("-z", "--compress"):
            compress = True

    if cred == '':
        print 'Specify a shortcut to credentials. '
        print '-- use addcred.py for this purpose.'
        print '-- check senddata.py -h for more options and requirements'
        sys.exit()
    if path == '':
        print 'Specify a base path.  '
        print '-- check senddata.py -h for more options and requirements'
        sys.exit()
    if protocol == '':
        print 'Specify a protocol (scp, ftp).  '
        print '-- check senddata.py -h for more options and requirements'
        sys.exit()

    # Test with missing information
    address=mpcred.lc(cred,'address')
    user=mpcred.lc(cred,'user')
    passwd=mpcred.lc(cred,'passwd')
    port=mpcred.lc(cred,'port')
    pathtolog = '/tmp/magpytransfer.log'

    if increment:
        depth = 1
    datelist = []
    current = datetime.utcnow()

    newcurrent = current
    for elem in range(depth):
        datelist.append(datetime.strftime(newcurrent,dateformat))
        newcurrent = current-timedelta(days=elem+1)

    print datelist

    for date in datelist:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in [f for f in filenames if f.endswith(date+"."+extension)]:
                localfile = os.path.join(dirpath, filename)
                print "Sending ", localfile
                if compress:
                    print 'creating compressed archive'
                    zfile = os.path.join(dirpath, filename.strip(extension)+'zip')
                    zf = zipfile.ZipFile(zfile, mode='w')
                    try:
                        zf.write(localfile, os.path.basename(localfile), compress_type=compression)
                    finally:
                        print 'closing'
                        zf.close()
                    localfile = zfile
                print "Sending ", localfile                
                if protocol == 'ftp':
                    # Tested - working flawless (take care with address - should not contain ftp://)
                    ftpdatatransfer(localfile=localfile,ftppath=remotepath,myproxy=address,port=port,login=user,passwd=passwd,logfile=pathtolog,raiseerror=True)
                    pass
                elif protocol == 'scp':
                    # Tested - working flawless
                    scptransfer(localfile,user+'@'+address+':'+remotepath+'/'+filename,passwd)
                    pass
                elif protocol == 'gin':
                    print "GIN not supported yet"
                    # Coming soon
                    sys.exit()
                else:
                    print "Unsupported protocol selected:"
                    print '-- Specify one among (scp, ftp).  '
                    print '-- check senddata.py -h for more options and requirements'
                    sys.exit()
                print "... success"

if __name__ == "__main__":
   main(sys.argv[1:])


