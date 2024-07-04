#!/bin/bash

set -e

if [ -d "/src" ]; then
    cp -rT /build /src
    pip install --no-cache-dir -e /src
else
    echo "请挂载目录 /src, 以释放源码."
    exit 1
fi

if [ -z "${EK_WEBPASS}" ]; then
    exec "embykeeper" "--basedir" "/app" "$@"
else
    exec "embykeeperweb" "--basedir" "/app" "--public" "$@"
fi
