#!/bin/sh
set -eu
# Use the already installed package; no editable checkout or network access.
exec "${BLUECHO_BIN:-bluecho}" serve "$@"
