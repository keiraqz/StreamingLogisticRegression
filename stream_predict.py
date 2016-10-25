from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.mllib.classification import LogisticRegressionModel
from pyspark.streaming.kafka import KafkaUtils # kafka connector via Spark
import redis # redis connector via Python

conf = SparkConf().setMaster("local[2]")
sc = SparkContext.getOrCreate(conf=conf)
ssc = StreamingContext(sc, 1)
KAFKA_BROKERS = "localhost:9092"

######## Clear Cache on Start ########
conn = redis.StrictRedis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True
        )
conn.flushall()

######## Load Model ########
model = LogisticRegressionModel.load(sc, "model/LBFGS")


######## Load Data from Kafka and Parse ########
# featurize
from pyspark.mllib.regression import LabeledPoint
def parsePoint(row):
    if row[-1] == -1:
        label = 0
    elif row[-1] == 1:
        label = 1
    else:
        raise ValueError(row[-1])
    return LabeledPoint(label=label, features=row[:-1])

# load data from Kafka
directKafkaStream = KafkaUtils.createDirectStream(
    ssc, 
    ["auto_trnx"], 
    {"metadata.broker.list": KAFKA_BROKERS}
)

# parse
test_data = directKafkaStream.map(
    lambda line: line[1].split(',')
).map(
    lambda row: [int(x) for x in row]
).map(
	parsePoint
)


######## Add result to Reids ########
def redisSink(rdd):
    def _add_redis(prediction):
        conn = redis.StrictRedis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True
        ) # seperate connection for each RDD
        cache_key = "%s:%s" % (prediction[0], prediction[1]) # key "predicted_result:actual_label"
        value = 1
        if conn.exists(cache_key):
            value = conn.get(cache_key)
            value = int(value) + 1
        conn.set(cache_key, value)
    rdd.foreach(_add_redis)


test_data.map(
    lambda row: [model.predict(row.features), row.label] # predict the result
).foreachRDD(
    redisSink # add to redis
)


ssc.start()
ssc.awaitTermination()