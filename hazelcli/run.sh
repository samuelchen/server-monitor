#!/bin/sh

# to run/compile hazelcli
# by samuel

#CLASS_PATH=.:./lib/hazelcast-3.1.3.jar:./lib/hazelcast-client.3.1.3.jar:./lib/emm_db-1.1-SNAPSHOT.jar:./lib/emm_common-1.1-SNAPSHOT.jar:./lib/gagein_cache-1.0-SNAPSHOT.jar
CLASS_PATH=.:./lib-cache/hazelcast-all-3.1.3.jar:./lib/emm_db-1.1-SNAPSHOT.jar:./lib/emm_common-1.1-SNAPSHOT.jar:./lib/gagein_cache-1.0-SNAPSHOT.jar
HAZEL_CLUSTER=$1
USER=$2
PASSWD=$3

if [ "$1" = "-h" ] ; then
	echo "Usage:"
	echo "  run with default cluster - $0 "
	echo "  run with specified cluster - $0 192.168.1.1:7701,192.168.1.10:7701"
	exit -1
fi

	# compile section
echo "Compiling ..."
javac -classpath $CLASS_PATH hazelcli.java

if [ $? -eq 0 ]; then
    echo "Succeed compile"
    echo "Running ..."
    #echo "java -classpath $CLASS_PATH hazelcli $HAZEL_CLUSTER"
    java -classpath $CLASS_PATH hazelcli $HAZEL_CLUSTER $USER $PASSWD
else
    echo "Fail compile"
    exit -1
fi
exit 0

