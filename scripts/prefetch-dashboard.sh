#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then echo 'Usage: prefetch-dashboard.sh /path/to/model-registry' >&2; exit 2; fi
# Explicit administrator acquisition; preserves model-specific restrictions.
"${BLUECHO_BIN:-bluecho}" models fetch --model sss-wreck-experimental --registry "$1"
"${BLUECHO_BIN:-bluecho}" models verify --model sss-wreck-experimental --registry "$1"
