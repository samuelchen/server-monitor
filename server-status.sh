#!/bin/sh


host=`hostname -i`
tm=`date '+%x %X'`
to="sqlmonitoring@gagein.com"
sub="Server status [$host] - $tm"
sendmail=./email.py

tsar | unix2dos > "server-status.txt"
$sendmail "$to" "$sub" "./server-status.txt"
