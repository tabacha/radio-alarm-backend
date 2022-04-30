#!/bin/bash
VERSION=$(dpkg-parsechangelog -S Version)
dch -D stable -r release
git commit -m "New Version $VERSION" debian/changelog
git tag v$VERSION
git push origin v$VERSION
dch -i "change this"
NEWVERSION=$(dpkg-parsechangelog -S Version)
git commit -m "Starting with version $NEWVERRSION" debian/changelog
