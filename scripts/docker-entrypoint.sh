#!/bin/bash

set -eu

if [ -z "${EK_WEBPASS}" ]; then
    exec "embykeeperweb" "--basedir" "/app" "--public" "$@"
else
    exec "embykeeper" "--basedir" "/app" "$@"
fi
