#!/usr/bin/env bash

# includes poetry binary in $PATH
export PATH="/root/.local/bin:$PATH"

set -e

if [[ "$1" == "gunicorn" ]]; then
    inv db
fi

exec "$@"