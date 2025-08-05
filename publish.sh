#!/usr/bin/env bash
# this_file: build.sh

cd $(dirname "$0") || exit 1

set -e # Exit on error

uvx hatch clean 
llms . "llms.txt"
gitnextver .
uvx hatch build
uvx hatch publish
