#!/bin/bash

set -e

if [ -z "${EK_WEBPASS}" ]; then
    exec "embykeeper" "--basedir" "/app" "$@"
else
    exec "embykeeperweb" "--basedir" "/app" "--public" "$@"
fi
