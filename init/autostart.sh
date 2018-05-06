#!/bin/sh

cp martas.sh /etc/init.d/martas
chmod 755 /etc/init.d/martas
chown root:root /etc/init.d/martas
update-rc.d martas defaults

