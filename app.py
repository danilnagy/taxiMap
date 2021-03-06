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
import os

import operator
import datetime
from dateutil import parser

app = Flask(__name__)


currentDirectory = os.path.dirname(os.path.abspath(__file__)) + "\\"

driver_data = []

start_time = time.time()

print "loading model..."

with open(currentDirectory + "data//dataModel.pkl", 'rb') as f:
	dataModel = pickle.load(f)

with open(currentDirectory + "data//scaler.pkl", 'rb') as f:
	scaler = pickle.load(f)

print "model loaded [" + str(int(time.time() - start_time)) + " sec]"


def point_distance(x1, y1, x2, y2):
	return ((x1-x2)**2.0 + (y1-y2)**2.0)**(0.5)

def remap(value, min1, max1, min2, max2):
	return float(min2) + (float(value) - float(min1)) * (float(max2) - float(min2)) / (float(max1) - float(min1))

def normalizeArray(inputArray, return_max=False):
	maxVal = 0
	minVal = 100000000000

	for j in range(len(inputArray)):
		for i in range(len(inputArray[j])):
			if inputArray[j][i] > maxVal:
				maxVal = inputArray[j][i]
				max_i = i
				max_j = j
			if inputArray[j][i] < minVal:
				minVal = inputArray[j][i]


	for j in range(len(inputArray)):
		for i in range(len(inputArray[j])):
			inputArray[j][i] = remap(inputArray[j][i], minVal, maxVal, 0, 1)

	if return_max:
		return [inputArray, [max_i, max_j]]
	else:
		return inputArray


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

	lat1 = str(request.args.get('lat1'))
	lng1 = str(request.args.get('lng1'))
	lat2 = str(request.args.get('lat2'))
	lng2 = str(request.args.get('lng2'))
	# lat3 = str(request.args.get('lat3'))
	# lng3 = str(request.args.get('lng3'))

	driver = random.choice(driver_data)
	lat3 = driver["lat"]
	lng3 = driver["lng"]

	print lat3, lng3

	w = float(request.args.get('w'))
	h = float(request.args.get('h'))
	cell_size = float(request.args.get('cell_size'))


	# # prediction variables
	# doy = 1 # January 1st

	date = parser.parse(driver["time"])
	dow = date.strftime("%w")
	tod = date.strftime("%H")

	# dow = 1 # Monday
	# tod = 15 # 6am - noon
	# temp = 60 # 60 deg F
	# condition = 0 # clear

	output = {"type":"FeatureCollection","features":[], "points":[]}

	output["analysis"] = []
	output["time"] = driver["time"]

	numW = int(math.floor(w/cell_size))
	numH = int(math.floor(h/cell_size))

	grid = []

	for j in range(numH):
		grid.append([])
		lat = remap(j, numH, 0, lat1, lat2)

		for i in range(numW):
			lng = remap(i, 0, numW, lng1, lng2)

			# print pos_y, pos_x

			data_point = np.asarray([dow, tod, lat, lng], dtype='float').reshape(1,-1)
			grid[j].append(predict(data_point, scaler, dataModel))


	[grid, max_indeces] = normalizeArray(grid, True)

	offsetLeft = (w - numW * cell_size) / 2.0
	offsetTop = (h - numH * cell_size) / 2.0

	for j in range(numH):
		for i in range(numW):
			newItem = {}

			newItem['x'] = offsetLeft + i*cell_size
			newItem['y'] = offsetTop + j*cell_size
			newItem['width'] = cell_size-1
			newItem['height'] = cell_size-1
			newItem['value'] = grid[j][i]

			output["analysis"].append(newItem)

	print max_indeces

	lat4 = remap(max_indeces[1], numH, 0, lat1, lat2)
	lng4 = remap(max_indeces[0], 0, numW, lng1, lng2)

	print lat4, lng4

	api_key = "AIzaSyB9WjQBjO2QMrBfXPpj9BuLUhLW3LfnE9g"

	request_str = "https://maps.googleapis.com/maps/api/directions/json?origin={}+{}&destination={}+{}&avoid=highways&alternatives=true&key={}".format(lat3, lng3, lat4, lng4, api_key)

	r = requests.get(request_str)
	data = r.json()

	# data = []

	all_routes = []
	all_predictions = []

	prediction_averages = []

	for route in data['routes']:
		route_str = route['overview_polyline']['points']
		route_points = pl().decode(route_str)

		feature = {"type":"Feature","properties":{},"geometry":{"type":"LineString"}}
		feature["geometry"]["coordinates"] = route_points
		feature["properties"]["category"] = "route"

		output["features"].append(feature)

		all_points = []

		for i, route_point in enumerate(route_points):

			all_points.append(route_point)

			if i < len(route_points) - 1:
				pts = interpolate(route_point, route_points[i+1])
				all_points += pts

		all_routes.append(all_points)

		predictions = []

		for route_point in all_points:

			# feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
			# feature["geometry"]["coordinates"] = route_point

			data_point = np.asarray([dow, tod, route_point[0], route_point[1]], dtype='float').reshape(1,-1)
			p = predict(data_point, scaler, dataModel)

			predictions.append(p)
			# feature["properties"]["prediction"] = p

			# output["points"].append(feature)

		all_predictions.append(predictions)

		prediction_averages.append(sum(predictions)/float(len(predictions)))

	[bestRoute, bestValue] = max(enumerate(prediction_averages), key=operator.itemgetter(1))

	print prediction_averages
	print bestRoute

	output["features"][bestRoute]["properties"]["category"] = "best"


	feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
	feature["geometry"]["coordinates"] = all_routes[bestRoute][0]
	feature["properties"]["id"] = "start"
	output["points"].append(feature)

	feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
	feature["geometry"]["coordinates"] = all_routes[bestRoute][-1]
	feature["properties"]["id"] = "end"
	output["points"].append(feature)

	for i, route_point in enumerate(all_routes[bestRoute]):

		if random.random() < all_predictions[bestRoute][i] / float(1000):

			feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
			feature["geometry"]["coordinates"] = route_point
			feature["properties"]["id"] = "pickup"
			output["points"].append(feature)

			break

	feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
	feature["geometry"]["coordinates"] = [driver["pickup_lat"],driver["pickup_lng"]]
	feature["properties"]["id"] = "actual"
	output["points"].append(feature)
	
	return json.dumps(output)

if __name__ == "__main__":

	fileName = "04_DO_Pairs_130116.csv"

	with open(currentDirectory +  "data//" + fileName, 'r') as f:
		records = f.readlines()
		records = [x.strip() for x in records]
		titles = records.pop(0).split(',')

	driver = {}

	for i, record in enumerate(records):
		data = record.split(',')
		if i%2 == 0:
			driver = {}
			driver["time"] = data[3]
			driver["lat"] = data[5]
			driver["lng"] = data[4]
		else:
			driver["pickup_lat"] = data[11]
			driver["pickup_lng"] = data[10]
			driver_data.append(driver)

	app.run(host='0.0.0.0',port=5000,debug=True,threaded=True)

