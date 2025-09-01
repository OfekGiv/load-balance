#!/bin/bash

printf "READ c_match.count\n" | nc -N 127.0.0.1 1234 \
  | tail -n1 \
  | awk '{ printf("c_match.count = %s\n", $1) }'
