from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.mllib.classification import LogisticRegressionModel
from pyspark.mllib.classification import (LogisticRegressionWithSGD, StreamingLogisticRegressionWithSGD)
from pyspark.streaming.kafka import KafkaUtils # kafka connector via Spark
import redis # redis connector via Python

conf = SparkConf().setMaster("local[2]")
sc = SparkContext.getOrCreate(conf=conf)
ssc = StreamingContext(sc, 1)
KAFKA_BROKERS = "localhost:9092"


######## Clear Cache on Start ########
def clearCache():
    conn = redis.StrictRedis(
                host='localhost', 
                port=6379, 
                db=0, 
                decode_responses=True
            )
    conn.flushall()


#### load trained model
def loadModel():
    ''' load trained LogisticRegressionModel model
    '''
    trained_model = LogisticRegressionModel.load(sc, "model/SGD")
    return trained_model


#### online training model with pre-trained model to start
class MyStreamingLogisticRegressionWithSGD(StreamingLogisticRegressionWithSGD):

    def __init__(self, *args, **kwargs):
        super(MyStreamingLogisticRegressionWithSGD, self).__init__(*args, **kwargs)
        self._model = LogisticRegressionModel(
            weights=trained_model.weights,
            intercept=trained_model.intercept,
            numFeatures=trained_model.numFeatures,
            numClasses=trained_model.numClasses,
        )

    def trainOnline(self, dstream):
        """Train the model on the incoming dstream."""
        self._validate(dstream)
        def save_and_update(rdd):
            update(rdd)

        def update(rdd):
            # LogisticRegressionWithSGD.train raises an error for an empty RDD.
            if not rdd.isEmpty():
                self._model = LogisticRegressionWithSGD.train(
                    rdd, self.numIterations, self.stepSize,
                    self.miniBatchFraction, self._model.weights,
                    regParam=self.regParam, convergenceTol=self.convergenceTol)

        dstream.foreachRDD(save_and_update)


######## Load Model ########
# model = LogisticRegressionModel.load(sc, "model/LBFGS")
model = MyStreamingLogisticRegressionWithSGD()
# model._model = trained_model

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
    lambda row: [model._model.predict(row.features), row.label] # predict the result
).foreachRDD(
    redisSink # add to redis
)
model.trainOnline(test_data)



ssc.start()
ssc.awaitTermination()