#!/bin/bash
VER=$(dpkg-parsechangelog -S Version)
RDEB="radio-alarm-backend_${VER}_all.deb"
dpkg-buildpackage --no-sign -rfakeroot && \
    dpkg -c ../${RDEB} && \
    scp ../${RDEB} root@radio.anders.hamburg:. && \
    ssh  root@radio.anders.hamburg dpkg -i ${RDEB}