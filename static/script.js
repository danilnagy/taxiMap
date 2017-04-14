

// var eventOutputContainer = document.getElementById("message");
// var eventSrc = new EventSource("/eventSource");

// eventSrc.onmessage = function(e) {
// 	console.log(e);
// 	eventOutputContainer.innerHTML = e.data;
// };

var tooltip = d3.select("div.tooltip");
var tooltip_title = d3.select("#title");
var tooltip_price = d3.select("#price");


var map = L.map('map').setView([40.759196, -73.980795], 15);

map._layersMaxZoom = 16;
map._layersMinZoom = 13;

L.tileLayer('https://api.tiles.mapbox.com/v4/{mapid}/{z}/{x}/{y}.png?access_token={accessToken}', {
	attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
	mapid: 'mapbox.light',
	accessToken: 'pk.eyJ1IjoiZGFuaWxuYWd5IiwiYSI6ImVobm1tZWsifQ.CGQL9qrfNzMYtaQMiI-c8A'
}).addTo(map);

// map.on('click', function(e) {
// 	// alert("Lat, Lon : " + e.latlng.lat + ", " + e.latlng.lng)
// 	updateData(e.latlng.lat, e.latlng.lng)
// });

//create variables to store a reference to svg and g elements

var svg_overlay = d3.select(map.getPanes().overlayPane).append("svg");
var g_overlay = svg_overlay.append("g").attr("class", "leaflet-zoom-hide");

var svg = d3.select(map.getPanes().overlayPane).append("svg");
var g1 = svg.append("g").attr("class", "leaflet-zoom-hide");
var g2 = svg.append("g").attr("class", "leaflet-zoom-hide");

// function projectPoint(lat, lng) {
// 	return map.latLngToLayerPoint(new L.LatLng(lat, lng));
// }

// function projectStream(lat, lng) {
// 	var point = projectPoint(lat,lng);
// 	this.stream.point(point.x, point.y);
// }

// var transform = d3.geo.transform({point: projectStream});
// var path = d3.geo.path().projection(transform);

function projectPoint(lat, lng) {
	return map.latLngToLayerPoint(new L.LatLng(lat, lng));
}

function projectStream(lat, lng) {
	var point = projectPoint(lat,lng);
	this.stream.point(point.x, point.y);
}

var transform = d3.geo.transform({point: projectStream});
var path = d3.geo.path().projection(transform);

function updateData(){

	var mapBounds = map.getBounds();
	var lat1 = mapBounds["_southWest"]["lat"];
	var lat2 = mapBounds["_northEast"]["lat"];
	var lng1 = mapBounds["_southWest"]["lng"];
	var lng2 = mapBounds["_northEast"]["lng"];

	// CAPTURE USER INPUT FOR CELL SIZE FROM HTML ELEMENTS
	var cell_size = 25;
	var w = window.innerWidth;
	var h = window.innerHeight;

	// SEND USER CHOICES FOR ANALYSIS TYPE, CELL SIZE, HEAT MAP SPREAD, ETC. TO SERVER
	request = "/getData?lat1=" + lat1 + "&lat2=" + lat2 + "&lng1=" + lng1 + "&lng2=" + lng2 + "&w=" + w + "&h=" + h + "&cell_size=" + cell_size

	console.log(request);

	d3.json(request, function(data) {

		console.log(data);

		$( "p.display" ).text(data.time);

		var topleft = projectPoint(lat2, lng1);

		svg_overlay.attr("width", w)
			.attr("height", h)
			.style("left", topleft.x + "px")
			.style("top", topleft.y + "px");

		var rectangles = g_overlay.selectAll("rect").data(data.analysis);
		rectangles.enter().append("rect");

		rectangles
			.attr("x", function(d) { return d.x; })
			.attr("y", function(d) { return d.y; })
			.attr("width", function(d) { return d.width; })
			.attr("height", function(d) { return d.height; })
			.attr("fill-opacity", ".2")
			.attr("fill", function(d) { return "hsl(" + Math.floor((1-d.value)*250) + ", 100%, 50%)"; });
		


		var lines = g1.selectAll("path")
			.data(data.features);
		
		lines.exit().remove();

		lines.enter()
			.append("path")
		;

		lines.attr("id", function(d){
				return d.properties.category;
			})
		;

		var markers = g1.selectAll("circle")
			.data(data.points);
		
		markers.exit().remove();

		markers.enter()
			.append("circle")
			.attr("class", "marker")
		;

		markers
			.attr("id", function(d){
				return d.properties.id;
			})
		;



  // 		var interp = g2.selectAll("circle")
  // 			.data(data.points_interp);
		
  // 		interp.exit().remove();

  // 		interp.enter()
		// 	.append("circle")
		// 	.attr("class", "interp")
		// 	.attr("r", function(d){
		// 		return d.properties.prediction * 5
		// 	})
		// ;

		map.on("viewreset", reset);
		reset();

		function reset() {

			var bounds = path.bounds(data),
			topLeft = bounds[0],
			bottomRight = bounds[1];

			var buffer = 150;

			// reposition the SVG to cover the features.
			svg .attr("width", bottomRight[0] - topLeft[0] + (buffer * 2))
				.attr("height", bottomRight[1] - topLeft[1] + (buffer * 2))
				.style("left", (topLeft[0] - buffer) + "px")
				.style("top", (topLeft[1] - buffer) + "px");

			g1   .attr("transform", "translate(" + (-topLeft[0] + buffer) + "," + (-topLeft[1] + buffer) + ")");
			// g2   .attr("transform", "translate(" + (-topLeft[0] + buffer) + "," + (-topLeft[1] + buffer) + ")");


			lines
				.attr("d", path)
			;

			markers
				.attr("cx", function(d) { return projectPoint(d.geometry.coordinates[0], d.geometry.coordinates[1]).x; })
				.attr("cy", function(d) { return projectPoint(d.geometry.coordinates[0], d.geometry.coordinates[1]).y; })
			;

	// 		interp
			// 	.attr("cx", function(d) { return projectPoint(d.geometry.coordinates[0], d.geometry.coordinates[1]).x; })
			// 	.attr("cy", function(d) { return projectPoint(d.geometry.coordinates[0], d.geometry.coordinates[1]).y; })
			// ;
		}

	});

};


//keyboard handling
//http://stackoverflow.com/questions/4954403/can-jquery-keypress-detect-more-than-one-key-at-the-same-time
var keys = {};

$(document).keydown(function (e) {
	keys[e.which] = true;
	checkKeys(e);
});

$(document).keyup(function (e) {
	delete keys[e.which];
});

function checkKeys(e) {
	if (keys.hasOwnProperty(13)){
		updateData();
	}
}

// updateData();