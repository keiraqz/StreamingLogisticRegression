from collections import namedtuple
from pyspark import SparkConf, SparkContext, SQLContext
from pyspark.ml.regression import LinearRegression
from pyspark.streaming import StreamingContext
from pyspark.mllib.classification import (
    LogisticRegressionWithSGD, 
    LogisticRegressionWithLBFGS
)

conf = SparkConf().setMaster("local[2]")
sc = SparkContext.getOrCreate(conf=conf)
# ssc = StreamingContext(sc, 1)
# sqlContext = SQLContext(sc)

# load rdd
path ="data/data.csv"
rdd = sc.textFile(path).map(
    lambda line: line.split(',')
)

# column names
keys = rdd.first()
# DataRow = namedtuple("DataRow", keys)

# get data
data = rdd.filter(
  lambda row: row[0] != keys[0]
).map(
    lambda row: [int(x) for x in row]
)
# .map(
#   lambda row: DataRow(*[int(val) for val in row])
#)

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

data = data.map(parsePoint)


# do a training/test split
# train_data, test_data = data.randomSplit((0.8, 0.2), seed=1800009193L) 
train_data, test_data = data.randomSplit((0.1, 0.9), seed=1800009193L) # only train on 10% of data


# fit the model
# model = LogisticRegressionWithLBFGS.train(train_data, regType="l1")
model = LogisticRegressionWithSGD.train(train_data, regType="l2")

# save model
# model.save(sc, "model/LBFGS")
model.save(sc, "model/SGD")

y = test_data.map(lambda row: row.label).collect()
yhat = model.predict(test_data.map(lambda row: row.features)).collect()