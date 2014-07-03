#!/bin/sh

# to run/compile hazelcli
# by samuel

CLASS_PATH=.:./lib-cache/hazelcast-all-3.1.3.jar:./lib/emm_db-1.1-SNAPSHOT.jar:./lib/emm_common-1.1-SNAPSHOT.jar:./lib/gagein_cache-1.0-SNAPSHOT.jar

if [ "$1" = "build" ] ; then

	# compile section
	javac -classpath $CLASS_PATH hazelcli.java


elif [ "$1" = '' ] ; then

	# run section
	echo "Compiling ..."
	javac -classpath $CLASS_PATH hazelcli.java
	if [ $? -eq 0 ]; then
		echo "Succeed compile"
		echo "Running ..."
		java -classpath $CLASS_PATH hazelcli
	else
		echo "Fail compile"
	fi
	
else
	echo "Usage:"
	echo "  run - $0"
	echo "  compile - $0 build"
fi
