#!/bin/bash

for pid in /proc/[0-9]*; do
    # Extracting the numeric PID from the directory name
    numeric_pid=$(basename $pid)

    # Counting the number of file descriptors
    fd_count=$(ls $pid/fd/ 2>/dev/null | wc -l)

    # Checking if the count is greater than 0
    if [ "$fd_count" -gt 0 ]; then
        echo "PID = $numeric_pid with $fd_count file descriptors"
    fi
done