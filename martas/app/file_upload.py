#!/usr/bin/env python
# coding=utf-8

"""
Upload files

DESCRIPTION
   Upload data to a destination using various different protocols.
   Supported protocols are FTP, SFTP, RSYNC, SCP, and GIN.

JOBLIST:
   Jobs are listed in a JSON structure and read by the upload process.
   You can have multiple jobs. Each job refers to a local path. Each job
   can have multiple destinations.

   {"graphmag" :  {"path":"/home/leon/Tmp/Upload/graph/aut.png",
                    "destinations": {"conradpage": { "type":"ftp", "path" : "/images/graphs/magnetism"} },
                    "log":"/home/leon/Tmp/Upload/testupload.log",
                    "endtime":"utcnow",
                    "starttime":2},
    "wicadjmin" :  {"path":"/home/leon/Tmp/Temp",
                    "destinations": {"gleave": { "type":"sftp", "path" : "/uploads/all-obs"} },
                    "log":"/home/leon/Tmp/wicadjart.log",
                    "endtime":"utcnow",
                    "starttime":2},
   }

APPLICATION:
   python3 file_uploads.py -j /my/path/uploads.json -m /tmp/sendmemory.json
"""

import magpy.opt.cred as mpcred
from martas.core.methods import martaslog as ml
from martas.core import methods as mm

import ftplib
from threading import Thread
import getopt
import json
import logging
import subprocess
from subprocess import check_output
from datetime import datetime, timedelta, timezone
import paramiko
import sys
import os
from pathlib import Path


# ################################################
#             Logging Setup
# ################################################

DEFAULT_LOG_DIR = os.path.expanduser("~/.martas/log")
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, "file_uploads.log")


def setup_logger(log_file=DEFAULT_LOG_FILE, debug=False):
    """
    Configure a dedicated logger that writes to both the specified log file
    and stdout without duplicating handlers across jobs.
    """
    log_file = os.path.expanduser(log_file)
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("file_uploads")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Clear existing handlers if reconfiguring for a job-specific log file
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


# Initialize default logger
logger = setup_logger()


# ################################################
#             Methods
# ################################################

def active_pid(name):
    """Check whether a process with the given name is currently running."""
    try:
        list(map(int, check_output(["pidof", name]).split()))
        return True
    except Exception:
        return False


def uploaddata(localpath, destinationpath, typus='ftp', address='', user='', pwd='', port=None, proxy=None, logfile='stdout'):
    """
    Upload a single file to a remote server using the specified protocol
    (ftp, ftpback, sftp, scp, rsync, gin, test).
    """
    success = True
    logger.info(
        "Running upload to %s (as %s) via %s: %s -> %s",
        address, user, typus, localpath, destinationpath
    )

    try:
        if typus == 'ftpback':
            Thread(
                target=ftptransfer,
                kwargs={
                    'source': localpath,
                    'destination': destinationpath,
                    'host': address,
                    'port': port,
                    'user': user,
                    'password': pwd,
                    'logfile': logfile,
                },
            ).start()
        elif typus == 'ftp':
            success = ftptransfer(
                source=localpath,
                destination=destinationpath,
                host=address,
                port=port,
                user=user,
                password=pwd,
                logfile=logfile,
            )
        elif typus == 'sftp':
            success = sftptransfer(
                source=localpath,
                destination=destinationpath,
                host=address,
                port=port or 22,
                user=user,
                password=pwd,
                proxy=proxy,
                logfile=logfile,
            )
        elif typus == 'scp':
            timeout = 60
            destina = "{}@{}:{}".format(user, address, destinationpath)
            mm.scptransfer(localpath, destina, pwd, timeout=timeout)
        elif typus == 'rsync':
            # Note: rsync requires passwordless SSH key authentication
            rsync_cmd = ["rsync", "-avz", "-e", "ssh", localpath, f"{user}@{address}:{destinationpath}"]
            logger.info("Executing: %s", " ".join(rsync_cmd))
            subprocess.run(rsync_cmd, check=True, capture_output=True, text=True)
        elif typus.startswith('gin'):
            if not active_pid('curl'):
                logger.info("Uploading minute data to GIN via curl")
                stdout = True
                if typus.endswith('basic'):
                    success = ginupload(localpath, user, pwd, address, authentication=' ', stdout=stdout)
                else:
                    success = ginupload(localpath, user, pwd, address, stdout=stdout)
                logger.info("Finished GINUPLOAD (success=%s)", success)
            else:
                logger.warning("curl is already active; skipping GIN upload for %s", localpath)
                success = False
        elif typus == 'test':
            logger.info("Test mode: skipping actual file transfer for %s", localpath)
        else:
            logger.error("Selected transfer type '%s' is not supported", typus)
            success = False

    except subprocess.CalledProcessError as e:
        logger.error("Subprocess transfer failed for %s: %s | stderr: %s", localpath, e, e.stderr)
        success = False
    except Exception as e:
        logger.exception("Unexpected error during %s upload of %s to %s: %s", typus, localpath, address, e)
        success = False

    return success


def getchangedfiles(basepath, memory, startdate=datetime(1777, 4, 30), enddate=None, extensions=None, namefractions=None, add="newer", debug=False):
    """
    Compare contents of basepath against memory and return dictionaries of
    newly modified files to upload and all analyzed files within the time window.
    """
    if not enddate:
        enddate = datetime.now(timezone.utc).replace(tzinfo=None)
    if not extensions:
        extensions = []
    if not namefractions:
        namefractions = []
    startdate = startdate.replace(tzinfo=None)
    enddate = enddate.replace(tzinfo=None)

    filelist = []
    try:
        if os.path.isfile(basepath):
            filelist = [basepath]
        elif os.path.isdir(basepath):
            for file in os.listdir(basepath):
                fullpath = os.path.join(basepath, file)
                filename, file_extension = os.path.splitext(fullpath)
                if os.path.isfile(fullpath):
                    ext_match = (
                        isinstance(extensions, list)
                        and len(extensions) > 0
                        and ("*" in extensions or any(ext in file_extension for ext in extensions))
                    )
                    frac_match = (
                        isinstance(namefractions, list)
                        and len(namefractions) > 0
                        and any(frac in filename for frac in namefractions)
                    )

                    if len(extensions) > 0 and len(namefractions) > 0:
                        if ext_match and frac_match:
                            filelist.append(fullpath)
                    elif len(extensions) > 0 and len(namefractions) == 0:
                        if ext_match:
                            filelist.append(fullpath)
                    elif len(namefractions) > 0 and len(extensions) == 0:
                        if frac_match:
                            filelist.append(fullpath)
                    else:
                        filelist.append(fullpath)
        else:
            logger.error("Source path does not exist: %s", basepath)
            return {}, {}
    except Exception as e:
        logger.exception("Error scanning source directory '%s': %s", basepath, e)
        return {}, {}

    if debug:
        logger.debug("getchangedfiles 1: %s (%s to %s)", filelist, startdate, enddate)

    retrievedSet = {}
    for name in filelist:
        try:
            stat = os.stat(name)
            mtime = stat.st_mtime
            mtime_dt = datetime.fromtimestamp(mtime, timezone.utc).replace(tzinfo=None)
            if startdate < mtime_dt <= enddate:
                retrievedSet[name] = mtime
        except OSError as e:
            logger.warning("Could not stat file '%s': %s", name, e)

    if debug:
        logger.debug("getchangedfiles 2 (retrievedSet): %s", retrievedSet)
        logger.debug("getchangedfiles 3 (memory): %s", memory)

    if memory:
        newdict = dict(retrievedSet.items() - memory.items())
    else:
        newdict = retrievedSet.copy()

    return newdict, retrievedSet


def sftptransfer(source, destination, host="yourserverdomainorip.com", user="root", password="12345", port=22, proxy=None, logfile='stdout'):
    """
    Transfer a file to an SFTP server.
    Returns True if successful, False otherwise.
    """
    if not os.path.isfile(source):
        logger.error("SFTP source file does not exist: %s", source)
        return False

    if not proxy:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(host, port=port, username=user, password=password, timeout=15)
            with ssh.open_sftp() as sftp:
                destina = os.path.join(destination, os.path.basename(source))
                sftp.put(source, destina)
        except Exception as e:
            logger.error("SFTP upload failed (%s -> %s:%s): %s", source, host, destination, e)
            return False
        finally:
            ssh.close()
    else:
        logger.info("Using SOCKS5 proxy: %s", proxy)
        import socks
        s = socks.socksocket()
        s.set_proxy(
            proxy_type=socks.SOCKS5,
            addr=proxy[0],
            port=proxy[1]
        )
        try:
            s.connect((host, port))
            transport = paramiko.Transport(s)
            transport.connect(username=user, password=password)
            with paramiko.SFTPClient.from_transport(transport) as client:
                destina = os.path.join(destination, os.path.basename(source))
                client.put(source, destina)
        except Exception as e:
            logger.error("SFTP upload via proxy failed (%s -> %s:%s): %s", source, host, destination, e)
            return False

    return True


def ftptransfer(source, destination, host="yourserverdomainorip.com", user="root", password="12345", port=21, proxy=None, logfile='stdout', cleanup=False, debug=False):
    """
    Transfer a file to an FTP server (attempts FTP_TLS first, falls back to plain FTP).
    Returns True if successful, False otherwise.
    """
    if not source or not os.path.isfile(source):
        logger.error("FTP source file missing or invalid: %s", source)
        return False

    filename = os.path.basename(source)

    if debug:
        logger.debug("ftptransfer: starting transfer of %s", filename)

    def ftpjob(site, src, dest, fname):
        if debug:
            site.set_debuglevel(1)
        site.cwd(dest)
        try:
            site.delete(fname)
        except ftplib.all_errors:
            # File does not exist yet on remote server; safe to ignore
            pass
        if debug:
            logger.debug("Uploading file: %s", fname)
        with open(src, 'rb') as file_obj:
            site.storbinary(f'STOR {fname}', file_obj)

    transfersuccess = False
    tls_error = None

    # 1. Try connecting via FTP_TLS
    try:
        with ftplib.FTP_TLS(timeout=30) as ftp:
            ftp.connect(host, port or 21)
            ftp.login(user, password)
            ftp.prot_p()
            logger.info("FTP TLS connection established to %s", host)
            ftpjob(ftp, source, destination, filename)
            transfersuccess = True
    except Exception as e:
        tls_error = e
        logger.debug("FTP_TLS failed for %s (%s), falling back to plain FTP", host, e)

    # 2. Fallback to plain FTP if TLS failed
    if not transfersuccess:
        try:
            with ftplib.FTP(timeout=30) as ftp:
                ftp.connect(host, port or 21)
                ftp.login(user, password)
                logger.info("Plain FTP connection established to %s", host)
                ftpjob(ftp, source, destination, filename)
                transfersuccess = True
        except Exception as plain_error:
            logger.error(
                "FTP transfer failed for %s -> %s:%s (TLS error: %s | Plain FTP error: %s)",
                source, host, destination, tls_error, plain_error
            )

    if cleanup and transfersuccess:
        try:
            os.remove(source)
        except OSError as e:
            logger.warning("Failed to remove local file %s after cleanup: %s", source, e)

    return transfersuccess


def ginupload(filename, user, password, url, authentication=' --digest ', stdout=True):
    """
    Upload data to Intermagnet GINs using curl.
    """
    logger.info("Starting ginupload for %s", filename)
    success = False

    curlstring = (
        f'curl -F "File=@{filename};type=text/plain" -F "Format=plain" '
        f'-F "Request=Upload" -u {user}:{password}{authentication}{url}'
    )

    try:
        p = subprocess.Popen(curlstring, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, error = p.communicate(timeout=60)
        out = out.decode('utf-8', errors='replace')
        error = error.decode('utf-8', errors='replace')

        if stdout:
            logger.info("GIN curl output: %s", out.strip())
        if "Success" in out:
            success = True
        else:
            logger.error("GIN upload did not return 'Success'. Output: %s | Error: %s", out.strip(), error.strip())
    except Exception as e:
        logger.exception("Exception during GIN upload for %s: %s", filename, e)

    return success


def main(argv):
    global logger
    statusmsg = {}
    jobs = ''
    tele = ''
    sendlogpath = ''
    logpath = DEFAULT_LOG_FILE
    receiver = ''
    receiverconf = ''
    proxies = {}
    debug = False

    try:
        opts, args = getopt.getopt(argv, "hj:m:t:D", ["jobs=", "memory=", "telegram=", "debug"])
    except getopt.GetoptError:
        print('file_uploads.py -j <jobs> -m <memory> -t <telegram> [-D]')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Usage: python3 file_uploads.py -j /my/path/uploads.json -m /tmp/sendmemory.json [-t telegram] [-D]')
            sys.exit()
        elif opt in ("-j", "--jobs"):
            jobs = arg
        elif opt in ("-m", "--memory"):
            sendlogpath = arg
        elif opt in ("-t", "--telegram"):
            tele = arg
        elif opt in ("-D", "--debug"):
            debug = True

    logger = setup_logger(DEFAULT_LOG_FILE, debug=debug)

    if tele:
        # Configure notification receiver for MARTAS logging
        mainpath = os.path.dirname(os.path.realpath(__file__))
        logpath = os.path.join(DEFAULT_LOG_DIR, "mm-fu-uploads.log")
        Path(logpath).parent.mkdir(parents=True, exist_ok=True)
        configpath = os.path.join(mainpath, "..", "conf", "monitor.cfg")
        if os.path.isfile(configpath):
            logger.info("Reading monitor configuration file: %s", configpath)
            monitorconf = mm.get_conf(configpath)
            receiver = monitorconf.get('notification')
            receiverconf = monitorconf.get('notificationconf')
            if monitorconf.get('https'):
                proxies['https'] = monitorconf.get('https')
            if monitorconf.get('http'):
                proxies['http'] = monitorconf.get('http')

    if not jobs or not os.path.isfile(jobs):
        logger.error("Please specify a valid path to a jobs JSON file (-j).")
        sys.exit(1)

    try:
        workdictionary = mm.get_json(jobs)
    except Exception as e:
        logger.exception("Failed to parse jobs JSON file '%s': %s", jobs, e)
        sys.exit(1)

    if not sendlogpath:
        sendlogpath = '/tmp/lastupload.json'
    else:
        Path(sendlogpath).parent.mkdir(parents=True, exist_ok=True)

    # Load existing memory file once before iterating over jobs
    fulldict = {}
    if os.path.isfile(sendlogpath) and os.stat(sendlogpath).st_size > 0:
        try:
            with open(sendlogpath, 'r', encoding='utf-8') as file:
                fulldict = json.load(file)
        except Exception as e:
            logger.exception("Failed to read memory file '%s', starting with empty memory: %s", sendlogpath, e)
            fulldict = {}

    # ################################################
    #             Process Each Job Independently
    # ################################################
    for key, job_cfg in workdictionary.items():
        name = f"FileUploads-{key}"
        job_had_errors = False

        # Switch to job-specific log file if configured, otherwise use default ~/.martas/log/file_uploads.log
        job_logfile = job_cfg.get('log', DEFAULT_LOG_FILE)
        logger = setup_logger(job_logfile, debug=debug)

        logger.info("==============================================")
        logger.info("PROCESSING JOB: %s", key)
        logger.info("==============================================")

        try:
            if not isinstance(job_cfg, dict):
                raise ValueError(f"Invalid job configuration format for '{key}': expected dict.")

            lastfiles = fulldict.get(key) or {}
            if not lastfiles:
                logger.info("No previous upload memory found for job '%s'; initializing new memory.", key)

            sourcepath = job_cfg.get('path')
            if not sourcepath:
                raise ValueError(f"Missing 'path' in configuration for job '{key}'.")

            extensions = job_cfg.get('extensions', [])
            namefractions = job_cfg.get('namefractions', [])
            starttime = job_cfg.get('starttime', datetime(1777, 4, 30))
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            endtime = job_cfg.get('endtime', now)

            if endtime in ["utc", "now", "utcnow"]:
                endtime = now
            if isinstance(starttime, int):
                starttime = now - timedelta(days=starttime)

            newfiledict, alldic = getchangedfiles(
                sourcepath, lastfiles, starttime, endtime, extensions, namefractions, debug=debug
            )
            logger.info("Job '%s': found %d new/changed files to upload.", key, len(newfiledict))

            destinations = job_cfg.get('destinations')
            if not destinations or not isinstance(destinations, dict):
                raise ValueError(f"Missing or invalid 'destinations' in configuration for job '{key}'.")

            for dest, destdict in destinations.items():
                logger.info("  --------------------------------------------")
                logger.info("  -> Destination: %s", dest)
                logger.info("  --------------------------------------------")

                try:
                    address = mpcred.lc(dest, 'address')
                    user = mpcred.lc(dest, 'user')
                    passwd = mpcred.lc(dest, 'passwd')
                    port = mpcred.lc(dest, 'port')
                    proxy = destdict.get('proxy', None)

                    if not address or not user:
                        logger.error("Missing credentials (address or user) for destination '%s' in job '%s'.", dest, key)
                        job_had_errors = True
                        continue

                    if not newfiledict:
                        logger.info("  No new files to transfer for destination '%s'.", dest)
                        continue

                    for nfile in newfiledict:
                        logger.info("    -> Uploading %s to destination '%s'", nfile, dest)
                        success = uploaddata(
                            nfile,
                            destdict.get('path'),
                            destdict.get('type', 'ftp'),
                            address,
                            user,
                            passwd,
                            port,
                            proxy=proxy,
                            logfile=destdict.get('logfile', 'stdout'),
                        )
                        logger.info("    -> Result for %s: success=%s", nfile, success)
                        if not success:
                            job_had_errors = True
                            logger.warning(
                                "Upload of %s to '%s' failed: keeping file in pending list for next run.",
                                nfile, dest
                            )
                            # Use pop() instead of del to avoid KeyError if multiple destinations fail for the same file
                            alldic.pop(nfile, None)

                except Exception as dest_err:
                    job_had_errors = True
                    logger.exception("Unhandled error in job '%s' for destination '%s': %s", key, dest, dest_err)

            # Persist updated memory immediately after each job so progress is saved even if later jobs fail
            fulldict[key] = alldic
            mm.put_json(sendlogpath, fulldict)
            logger.info("Memory updated for job '%s' in %s", key, sendlogpath)

            if job_had_errors:
                statusmsg[name] = f"partial or full upload error in job '{key}' - check log ({job_logfile})"
            else:
                statusmsg[name] = "uploading data successful"

        except Exception as job_err:
            logger.exception("CRITICAL ERROR in job '%s': %s", key, job_err)
            statusmsg[name] = f"error when uploading files in '{key}': {job_err}"

    # Restore default logger for final summary
    logger = setup_logger(DEFAULT_LOG_FILE, debug=debug)

    if tele:
        if debug:
            logger.debug("Notification statusmsg: %s", statusmsg)
        elif receiver:
            martaslog = ml(logfile=logpath, receiver=receiver, proxies=proxies)
            if receiver == 'email':
                martaslog.email['config'] = receiverconf
            elif receiver == 'telegram':
                martaslog.telegram['config'] = receiverconf
            martaslog.msg(statusmsg)

    logger.info("----------------------------------------------------------------")
    logger.info("File upload application finished")
    logger.info("----------------------------------------------------------------")


if __name__ == "__main__":
    main(sys.argv[1:])
