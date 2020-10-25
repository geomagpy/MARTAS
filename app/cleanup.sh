# Delete files older than 100 days.
# Cronjob running under "/etc/crontab"
# add a line like:
# 15 0 * * *   root    /bin/sh /home/cobs/MARTAS/app/cleanup.sh
# to run the job every day 15 minutes past midnight

find /srv/mqtt -name "*.bin" -mtime +100 -exec rm {} \;

