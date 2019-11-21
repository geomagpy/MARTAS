#!/usr/bin/env python
# coding=utf-8


def sendmail(dic):
    """
    Function for sending mails with attachments
    """
    
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email.utils import COMMASPACE, formatdate
        from email import encoders
        from smtplib import SMTP
    except:
        pass
    #if not smtpserver:
    #    smtpserver = 'smtp.web.de'
    if 'Attach' in dic:
        files = map(lambda s:s.strip(), dic['Attach'].split(','))
    else:
        files = []
    if not dic['Text']:
        text = 'Cheers, Your Analysis-Robot'
    if not 'Subject' in dic:
        dic['Subject'] = 'Automatic message'
    if 'mailcred' in dic:
        ## import credential routine
        #read credentials
        pass
    if 'port' in dic:
        port = int(dic['port'])
    else:
        port = None
    if 'user' in dic:
        user = dic['user']
    else:
        user = ''

    msg = MIMEMultipart()
    msg['From'] = dic['From']
    send_from = dic['From']
    #msg['To'] = COMMASPACE.join(send_to)
    msg['To'] = dic['To']
    send_to = map(lambda s:s.strip(), dic['To'].split(','))
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = dic['Subject']
    msg.attach( MIMEText(dic['Text']) )

    # TODO log if file does not exist
    for f in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(f,"rb").read() )
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)

    smtp = SMTP()
    smtp.set_debuglevel(False)
    if port:
        smtp.connect(dic.get('smtpserver'), port)
    else:
        smtp.connect(dic.get('smtpserver'))
    smtp.ehlo()
    if port == 587:
        smtp.starttls()
    smtp.ehlo()
    if user:
        smtp.login(user, dic.get('pwd'))
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


def sendtelegram(dic):
    """
    sends messages over telegram
    """

    # TODO "dictionary" below in not meant to be the same as "dic" above
    import telegram_send
    # except: # import error
    #try: # conf file exists
    # except: # send howto
    # requires a existing configuration file for telegram_send
    # to create one use:
    # python
    # import telegram_send
    # telegram_send.configure("/path/to/my/telegram.cfg",channel=True)
    """
    This must be done before!
    tgmsg = ''
    for elem in dictionary:
        tgmsg += "{}: {}\n".format(elem, dictionary[elem])
    """
    #telegram_send.send(messages=[tgmsg],conf=self.telegram.get('config'),parse_mode="markdown")
    telegram_send.send(messages=[dic['text']],conf=dic['telegramconf'],parse_mode="markdown")


def sendswitchcommand(dic):
    """
    sends a switching command to an arduino using ardcomm.py
    """

    # TODO "comm" must be a part of dic, "conf" below must also be got from "dic" above
    script = os.path.join(conf.get('martasdir'),'app','ardcomm.py')
    pythonpath = sys.executable
    #arg1 = "-c {}".format(comm)
    arg1 = "-c {}".format(dic.get('comm'))
    #arg2 = "-p {}".format(conf.get('port'))
    arg2 = "-p {}".format(dic.get('port'))
    arg3 = "-b {}".format(dic.get('baudrate'))
    arg4 = "-a {}".format(dic.get('parity'))
    arg5 = "-y {}".format(dic.get('bytesize'))
    arg6 = "-s {}".format(dic.get('stopbits'))
    arg7 = "-t {}".format(dic.get('timeout'))
    #arg8 = "-e {}".format(conf.get('eol')) # not used so far

    command = "{} {} {} {} {} {} {} {} {}".format(pythonpath,script,arg1, arg2, arg3, arg4, arg5, arg6, arg7) ## To be checked
    command = "{} {} {}".format(pythonpath,script,arg1)
    if debug:
        print (" ... sending {}".format(command))

    try:
        import subprocess
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        mesg = "{}".format(output)
    except subprocess.CalledProcessError:
        mesg = "threshold: sending command didnt work"
    except:
        mesg = "threshold: sending command problem"

    print (mesg)
    print (" ... success")



def readConfigFromFile(path):
    """
    read out a file into a dict
    as generally as possible

    how a config file should look like:
    ##  -------------------------------
    # # are comments

    key  :  value

    # there must be at least one ' ' (space) beside the ':' 
    # so the divider is ' : '
    ##  -------------------------------
    """

    dic = {}
    try:
        config = open(path,'r')
        confs = config.readlines()

        for conf in confs:
            if conf.startswith('#'):
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                conflst = conf.split(' : ')
                key = conflst[0].strip()
                value = conflst[1].strip()
                dic[key] = value
    except:
        print ("Problems when loading conf data from file.")

    return dic

