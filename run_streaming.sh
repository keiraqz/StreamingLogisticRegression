#!/bin/bash


sudo /usr/local/zookeeper/bin/zkServer.sh start 
sudo /usr/local/kafka/bin/kafka-server-start.sh /usr/local/kafka/config/server.properties &
nohup redis-server &

source activate rasp_pi
nohup python auto_producer.py &
$SPARK_HOME/bin/spark-submit stream_predict.py

