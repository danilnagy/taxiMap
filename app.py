from flask import Flask
from flask import render_template
from flask import request
from flask import Response

import pickle
import numpy as np

import json
import time
import sys
import random
import math

import pyorient

from sklearn import preprocessing
from sklearn import svm
from multiprocessing import Pool

from polyline.codec import PolylineCodec as pl
import requests



app = Flask(__name__)

def lineLength(pt1, pt2):
	return ( (pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2 ) ** .5

def interpolate(pt1, pt2):
	dist = .0005
	l = lineLength(pt1, pt2)

	pts = []
	
	if l > dist:
		div = int(math.floor(l / dist))
		# br = l / div
		dx = (pt2[0] - pt1[0]) / div
		dy = (pt2[1] - pt1[1]) / div

		x = pt1[0]
		y = pt1[1]

		for i in range(div-1):
			x += dx
			y += dy
			pts.append([x, y])

	return pts

def func(data, model):
	return model.predict(data)

def predict(data, scaler, model):

	d_scaled = scaler.transform(data)
	# print d_scaled
	prediction = model.predict(d_scaled)
	return max(0, prediction[0])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/getData/")
def getData():

	lat1 = str(request.args.get('lat'))
	lng1 = str(request.args.get('lng'))

	print lat1, lng1

	start_time = time.time()

	print "loading model..."

	local_path = "C:\\Users\\danil\\Google Drive\\SYNC\\Taxi\\"

	with open(local_path + 'dataModel.pkl', 'rb') as f:
		dataModel = pickle.load(f)

	with open(local_path + 'scaler.pkl', 'rb') as f:
		scaler = pickle.load(f)

	print "model loaded [" + str(int(time.time() - start_time)) + " sec]"


	lat2 = 40.767756
	lng2 = -73.993176

	api_key = "AIzaSyB9WjQBjO2QMrBfXPpj9BuLUhLW3LfnE9g"

	request_str = "https://maps.googleapis.com/maps/api/directions/json?origin={}+{}&destination={}+{}&avoid=highways&alternatives=true&key={}".format(lat1, lng1, lat2, lng2, api_key)

	r = requests.get(request_str)
	data = r.json()

	# data = []

	# doy = 1 # January 1st
	dow = 1 # Monday
	tod = 1 # 6am - noon
	# temp = 60 # 60 deg F
	# condition = 0 # clear

	output = {"type":"FeatureCollection","features":[], "points":[], "points_interp":[]}

	for route in data['routes']:
		route_str = route['overview_polyline']['points']
		route_points = pl().decode(route_str)

		feature = {"type":"Feature","properties":{},"geometry":{"type":"LineString"}}
		feature["geometry"]["coordinates"] = route_points

		output["features"].append(feature)

		for route_point in route_points:
			feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
			feature["geometry"]["coordinates"] = route_point

			data_point = np.asarray([dow, tod, route_point[0], route_point[1]], dtype='float').reshape(1,-1)
			p = predict(data_point, scaler, dataModel)
			feature["properties"]["prediction"] = p

			output["points"].append(feature)

		for i, route_point in enumerate(route_points[:-1]):

			pts = interpolate(route_point, route_points[i+1])

			for pt in pts:
				feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
				feature["geometry"]["coordinates"] = pt

				data_point = np.asarray([dow, tod, pt[0], pt[1]], dtype='float').reshape(1,-1)
				p = predict(data_point, scaler, dataModel)
				feature["properties"]["prediction"] = p

				output["points_interp"].append(feature)

	return json.dumps(output)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000,debug=True,threaded=True)