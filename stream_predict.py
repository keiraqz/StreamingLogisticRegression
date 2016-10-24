from collections import namedtuple
from pyspark import SparkConf, SparkContext, SQLContext
from pyspark.ml.regression import LinearRegression
from pyspark.streaming import StreamingContext
from pyspark.mllib.classification import LogisticRegressionModel
from pyspark.streaming.kafka import (KafkaUtils, TopicAndPartition)

conf = SparkConf().setMaster("local[2]")
sc = SparkContext.getOrCreate(conf=conf)
ssc = StreamingContext(sc, 1)
brokers = "localhost:9092"
######## Load Data ########
# load rdd
# path ="file:////Users/rqh489/Documents/Work/Project/Others/SparkModelingdata/test/" # needs to be a directory

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

# test_data = ssc.textFileStream(path).map(parsePoint)
directKafkaStream = KafkaUtils.createDirectStream(ssc, ["auto_trnx"], {"metadata.broker.list": brokers})
test_data = directKafkaStream.map(
    lambda line: line[1].split(',')
).map(
    lambda row: [int(x) for x in row]
).map(
	parsePoint
)

######## Load Model ########

model = LogisticRegressionModel.load(sc, "model/LBFGS")

# y = test_data.map(lambda row: row.label).collect()
test_data.map(lambda row: model.predict(row.features)).pprint()
# yhat = model.predict(test_data.map(lambda row: row.features))
# print(yhat)

ssc.start()
ssc.awaitTermination()