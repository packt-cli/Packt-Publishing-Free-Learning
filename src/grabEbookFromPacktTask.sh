#!/bin/bash

function log {
	echo  $(date +"%Y%m%d_%H%M%S") : $@
}

typeset -i sleepTime=120

typeset -i i=0
until [  $i -gt 10 ]; do
 log grab book 
 cd /home/pi/Packt/src && /usr/bin/python3 packtPublishingFreeEbook.py -g
 return=$?
 log returned code [$return]
 if [ $return -eq 0 ] ; then 
	break;
 fi 
 
 log loop until captcha works.
 log Wait $sleepTime seconds before next retry [$i]
 sleep $sleepTime 
 i+=1
done
