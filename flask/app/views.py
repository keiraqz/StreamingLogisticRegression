from flask import jsonify

from app import app
from flask import render_template, request
import hashlib
from struct import *
import json
from time import gmtime, strftime
import redis

redisClient = redis.StrictRedis(host='localhost', port=6379, db=0)
	

# Front page
@app.route("/")
@app.route("/index")
def index():
	title = "Streaming Demo"
	return render_template("imgtrenddisplay.html", title = title)


# get count
@app.route('/count', methods=['GET'])
def get_count():
	title = "Streaming Demo"
	# key "predicted_result:actual_label"
	response = redisClient.mget([
		"1:0.0:pre","0:1.0:pre","0:0.0:pre","1:1.0:pre", # with pretrained model
		"1:0.0","0:1.0","0:0.0","1:1.0" # NO pretrained model
	]) 
	TP = float(response[3]) if response[3] else 0
	TN = float(response[2]) if response[3] else 0
	FP = float(response[0]) if response[3] else 0
	FN = float(response[1]) if response[3] else 0
	ACC_pre = (TP + TN) / (TP + TN + FP + FN)
	TP = float(response[7]) if response[3] else 0
	TN = float(response[6]) if response[3] else 0
	FP = float(response[4]) if response[3] else 0
	FN = float(response[5]) if response[3] else 0
	ACC = (TP + TN) / (TP + TN + FP + FN)
	print(ACC_pre)
	print(ACC)
	jsonresponse = [
		{"type": "ACC pretrained", "value": ACC_pre},
		{"type": "ACC", "value": ACC}
		]
	return jsonify(output=jsonresponse)



if __name__ == '__main__':
	"Are we in the __main__ scope? Start test server."
	app.run(host='localhost',port=5000,debug=True)