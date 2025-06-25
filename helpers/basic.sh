#!/bin/sh
# A basic tool for testing stdout, stderr, and exit codes.
if [ "$1" = "stdout" ]; then
  printf "$2"
  exit 0
elif [ "$1" = "stderr" ]; then
  printf "$2" >&2
  exit 1
fi
