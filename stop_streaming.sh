#!/bin/bash

kill $(ps aux | grep '[p]ython auto_producer.py' | awk '{print $2}')
kill $(ps aux | grep 'redis-server' | awk '{print $2}')

sudo /usr/local/kafka/bin/kafka-server-stop.sh
sleep 3
sudo /usr/local/zookeeper/bin/zkServer.sh stop