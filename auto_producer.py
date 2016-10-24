import random
import numpy
import sys
import six
import json
import os
import time
from datetime import datetime
from twilio.rest import TwilioRestClient
from kafka import KafkaProducer
import multiprocessing
from multiprocessing import Process


class Producer(object):
	def __init__(self):
		self.producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
		self.merchants_list = []

	def load_website_list(self):
		with open('data/test/test_data.csv') as data_file:
			self.merchants_list = data_file.read().splitlines() 

	def produce_msgs(self):
		msg_cnt = 0
		while True:
			time_field = datetime.now().strftime("%Y%m%d %H%M%S")
			random_merchant = numpy.random.choice(self.merchants_list)
			print random_merchant
			time.sleep(0.5)
			self.producer.send('auto_trnx', random_merchant.strip().encode('utf8'))
			msg_cnt += 1
		
		
if __name__ == "__main__":
	prod = Producer()
	prod.load_website_list()
	prod.produce_msgs()
