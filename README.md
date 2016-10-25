# README or not

![Image of Pipeline](/flask/app/static/img/pipeline.png)
![model](/flask/app/static/img/model_accuracy.png)


### Train offline model in Spark

```
# save model to file
$SPARK_HOME/bin/spark-submit spark_training.py
```

- shortcut for streaming demo

```
bash run_streaming.sh
python flask/run.py
```

### Run the streaming example

-  Start zookeeper & Kafka

```
sudo /usr/local/zookeeper/bin/zkServer.sh start 
sudo /usr/local/kafka/bin/kafka-server-start.sh /usr/local/kafka/config/server.properties &
```

- Start Redis

```
redis-server
```

- Start Spark Streaming

```
$SPARK_HOME/bin/spark-submit stream_predict.py
```

- Start Kafka Producer

```
python auto_producer.py
```

- Start flask app

```
cd flask
python run.py

# in the browser
localhost:5000
```

-  Stop zookeeper & Kafka

```
sudo /usr/local/kafka/bin/kafka-server-stop.sh
sudo /usr/local/zookeeper/bin/zkServer.sh stop
```


### Tools and Dependncies
- Scala 2.11
- Spark 2.0.1
- Zookeeper 3.4.8
- Kafka 0.9
- Redis 2.6.9

- for Spark Streaming
	- spark-streaming-kafka-0-8_2.11-2.0.1.jar
		- kafka_2.11-0.8.2.2.jar
			- metrics-core-2.2.0.jar

- for Python (pip install)
	- kafka-python==1.0.2
	- redis==2.10.5
