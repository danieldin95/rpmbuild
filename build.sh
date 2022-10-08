#!/bin/bash

set -ex

specs=$(find ./SPECS -name '*.spec')

## Installing deps
for spec in $specs; do
  yum-builddep -y $spec
done

## Building packages
for spec in $specs; do
  rpmbuild -D "_topdir $PWD" -ba $spec
done
