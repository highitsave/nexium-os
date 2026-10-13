#!/bin/bash
set -euo pipefail
sudo cp scripts/test-browser-chooser.py work/root/usr/local/lib/nexium/test-browser-chooser.py
sudo chroot work/root runuser -u nexium -- env HOME=/home/nexium DISPLAY=:99 XDG_RUNTIME_DIR=/tmp/nexium-runtime QT_QPA_PLATFORM=xcb /bin/sh -c 'mkdir -p "$XDG_RUNTIME_DIR"; chmod 700 "$XDG_RUNTIME_DIR"; /opt/nexium-browser/venv/bin/python /usr/local/lib/nexium/test-browser-chooser.py --qt' 2>&1 | tee reports/browser/chooser-qt-tests.txt
sudo rm work/root/usr/local/lib/nexium/test-browser-chooser.py
