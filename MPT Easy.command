#!/bin/sh

# Double-click this file in Finder to start MoneyPrinterTurbo Easy.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

export MPT_EASY_OPEN_BROWSER=1
exec /bin/sh "$SCRIPT_DIR/easy_webui.sh"
