#!/bin/bash
docker build -t wc-watcher .
CONTAINER=$(docker create wc-watcher)
docker cp ${CONTAINER}:/deployment.zip .
docker rm ${CONTAINER}