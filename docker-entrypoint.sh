#!/bin/bash
set -e

if [ "$1" = "start" ]; then
    uwsgi --ini /etc/uwsgi/apps-available/visualisation-app.ini
else
    exec "$@"
fi