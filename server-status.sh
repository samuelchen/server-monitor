#!/bin/sh


host=`hostname -i`
tm=`date '+%x %X'`
to="sqlmonitoring@gagein.com"
sub="Server status [$host] - $tm"
sendmail=./email.py

tsar | unix2dos > "report.txt"
$sendmail "$to" "$sub" "./report.txt"
