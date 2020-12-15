#! /bin/bash

if ldmadmin isrunning; then
    echo "ldmadmin isrunning is true"
		    if ! pqmon >& /dev/null ; then

						echo "bad queue - creating new queue"
						ldmadmin stop
						ldmadmin clean
						
						# try to make the needed dir just in case
						queue_location=`regutil /queue/path`
						queue_path=`dirname $queue_location`
						if ! mkdir -p $queue_path; then
								echo "ERROR making queue path: $queue_path"
								exit 1
						fi

						ldmadmin delqueue
						ldmadmin mkqueue -f
						# if you are running pqsurf - uncomment these lines
						# ldmadmin delsurfqueue
						# ldmadmin mksurfqueue -f

						ldmadmin start
				else
						echo "queue seems ok"
				fi
else
    echo "ldmadmin isrunning is false"
    
    ldmadmin stop
    ldmadmin clean
    
    # Check the queue
    echo "checking product queue"
    if ! ldmadmin queuecheck; then

	echo "bad queue - creating new queue"

	# try to make the needed dir just in case
	queue_location=`regutil /queue/path`
	queue_path=`dirname $queue_location`
	if ! mkdir -p $queue_path; then
	    echo "ERROR making queue path: $queue_path"
	    exit 1
	fi

	ldmadmin delqueue
	ldmadmin mkqueue -f

        # if you are running pqsurf - uncomment these lines
        # ldmadmin delsurfqueue
        # ldmadmin mksurfqueue -f
    fi

    ldmadmin start

    #
    # sleep a couple of seconds, then check status
    #
    sleep 2
    if ldmadmin isrunning; then
	echo "ldm restarted successfully."
    else
	echo "ldm did not restart."
    fi 
       
fi
