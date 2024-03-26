#!/bin/bash
for ((x=1; x<=$2; x++)); do python -m mocks.$1.main; done
