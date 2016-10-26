from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.mllib.classification import LogisticRegressionModel
from pyspark.mllib.classification import (LogisticRegressionWithSGD, StreamingLogisticRegressionWithSGD)
from pyspark.streaming.kafka import KafkaUtils # kafka connector via Spark
import redis # redis connector via Python


KAFKA_BROKERS = "localhost:9092"
NUM_FEATURES = 30


######## Clear Cache on Start ########
def clear_cache():
    conn = redis.StrictRedis(
                host='localhost', 
                port=6379, 
                db=0, 
                decode_responses=True
            )
    conn.flushall()


######## Initiate a streaming model with pre-trained model ########
def get_model(pretrained=True):
    ''' Initiate a streaming model.
    If pretrained=True, init a streaming model with the trained parameters;
    if not, set initial weight to be all zeros.
    '''
    if (pretrained):
        trained_model = _load_pre_trained_model()
        model = MyStreamingLogisticRegressionWithSGD(trained_model=trained_model)
    else:
        model = StreamingLogisticRegressionWithSGD()
        model.setInitialWeights([0.0] * NUM_FEATURES)
    return model

def _load_pre_trained_model():
    ''' load trained LogisticRegressionModel model'''
    trained_model = LogisticRegressionModel.load(sc, "model/SGD")
    # trained_model = LogisticRegressionModel.load(sc, "model/LBFGS")
    return trained_model


######## Input data parser ########
from pyspark.mllib.regression import LabeledPoint
def parse_point(row):
    '''Parse input data. Last entry is the label'''
    if row[-1] == -1:
        label = 0
    elif row[-1] == 1:
        label = 1
    else:
        raise ValueError(row[-1])
    return LabeledPoint(label=label, features=row[:-1])


######## Add result to Redis ########
def redis_sink(rdd):
    ''' save predict results to Redis with keys: "predicted:actual"
    TP: {"1:1.0", count}
    TN: {"0:0.0", count}
    FP: {"1:0.0", count}
    FN: {"0:1.0", count}
    '''
    def _add_redis(prediction):
        ''' connect to redis and set key, value pair'''
        conn = redis.StrictRedis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True
        ) # seperate connection for each RDD
        cache_key_pre = "%s:%s:pre" % (prediction[0], prediction[2]) # key "predicted_result:actual_label:pre"
        cache_key = "%s:%s" % (prediction[1], prediction[2]) # key "predicted_result:actual_label"
        value_pre = 1
        value = 1
        if conn.exists(cache_key_pre):
            value_pre = conn.get(cache_key_pre)
            value_pre = int(value_pre) + 1
        if conn.exists(cache_key):
            value = conn.get(cache_key)
            value = int(value) + 1
        cache_entry = { 
            cache_key_pre: value_pre,
            cache_key: value
        }
        conn.mset(cache_entry)
    rdd.foreach(_add_redis)


#### online training model with pre-trained model to start
class MyStreamingLogisticRegressionWithSGD(StreamingLogisticRegressionWithSGD):
    ''' Customized StreamingLogisticRegressionWithSGD 
    with the ability to load pre-trained model
    '''
    def __init__(self, trained_model, *args, **kwargs):
        super(MyStreamingLogisticRegressionWithSGD, self).__init__(*args, **kwargs)
        self.trained_model = trained_model
        self._model = LogisticRegressionModel(
            weights=self.trained_model.weights,
            intercept=self.trained_model.intercept,
            numFeatures=self.trained_model.numFeatures,
            numClasses=self.trained_model.numClasses,
        )

    def trainOn(self, dstream):
        """Train the model on the incoming dstream."""
        self._validate(dstream)

        def update(rdd):
            # LogisticRegressionWithSGD.train raises an error for an empty RDD.
            if not rdd.isEmpty():
                self._model = LogisticRegressionWithSGD.train(
                    rdd, self.numIterations, self.stepSize,
                    self.miniBatchFraction, self._model.weights,
                    regParam=self.regParam, convergenceTol=self.convergenceTol)

        dstream.foreachRDD(update)




if __name__ == "__main__":
    # Streaming context
    conf = SparkConf().setMaster("local[2]")
    sc = SparkContext.getOrCreate(conf=conf)
    ssc = StreamingContext(sc, 1)

    clear_cache() # clear the cache
    model_with_pretrain = get_model(pretrained=True) # get model with pre-trained model
    model = get_model(pretrained=False) # get model with pre-trained model

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
        parse_point
    )


    # Predict and Train
    test_data.map(
        lambda row: [
            model_with_pretrain._model.predict(row.features), # predict with pre-trained model
            model._model.predict(row.features), # predict with NO pre-trained model
            row.label] # predict the result
    ).foreachRDD(
        redis_sink # add to redis
    )
    model_with_pretrain.trainOn(test_data) # online train model
    model.trainOn(test_data) # online train model

    # Start the streaming context
    ssc.start()
    ssc.awaitTermination()


