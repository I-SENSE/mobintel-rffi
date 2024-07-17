#!/bin/bash

max_fd=0
max_pid=0

for pid in /proc/[0-9]*; do
    numeric_pid=$(basename "$pid")

    # Counting the number of file descriptors
    fd_count=$(ls "$pid/fd/" 2>/dev/null | wc -l)

    # Check if this count is the maximum
    if [ "$fd_count" -gt "$max_fd" ]; then
        max_fd=$fd_count
        max_pid=$numeric_pid
    fi
done

# Display the process with the maximum number of file descriptors
echo "Process with max file descriptors: PID = $max_pid with $max_fd file descriptors"

# Set the file descriptor limit to 4096 for the process with the maximum count
if [ "$max_pid" -ne 0 ]; then
    prlimit --nofile=4096 --pid "$max_pid"
    echo "Set nofile limit to 4096 for process PID = $max_pid"
else
    echo "No process with open file descriptors found."
fi