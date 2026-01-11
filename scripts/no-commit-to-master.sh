#!/bin/sh
branch=$(git rev-parse --abbrev-ref HEAD)

if [ "$branch" = "master" ] || [ "$branch" = "main" ]; then
    echo "Error: Direct commits to $branch are not allowed."
    echo "Please create a feature branch and submit a pull request."
    exit 1
fi
