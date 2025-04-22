from flask import Flask, request, jsonify
import ee
import geojson
import json
from datetime import datetime, timedelta
import os

# Initialize Earth Engine
try:
    # Authenticate with your project ID
    ee.Initialize(project='auth-5640e')
except Exception as e:
    print("Please authenticate Earth Engine first")
    raise e

app = Flask(__name__)

# Enable CORS if needed
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST')
    return response

def get_recent_image(geometry):
    """Get recent satellite image for the given geometry"""
    # Get current date and 3 months back for image collection
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Convert dates to strings
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Get least cloudy image from Sentinel-2
    collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                  .filterDate(start_date_str, end_date_str)
                  .filterBounds(geometry)
                  .sort('CLOUDY_PIXEL_PERCENTAGE')
                  .first())
    
    
    # Clip to the geometry
    clipped_image = collection.clip(geometry)
    
    return clipped_image

def get_image_url(image, geometry):
    """Get thumbnail URL for the image"""
    # Visualization parameters
    vis_params = {
        'min': 0,
        'max': 3000,
        'bands': ['B4', 'B3', 'B2']  # RGB bands
    }
    
    # Get the thumbnail URL
    url = image.getThumbURL({
    'region': geometry,
    'dimensions': 1024,  # instead of 512
    'format': 'png',
    **vis_params
    })
    
    return url

@app.route('/get-satellite-image', methods=['POST'])
def get_satellite_image():
    try:
        # Get JSON data from request
        data = request.get_json()
        geo_json = data.get('geo_json')
        
        if not geo_json:
            return jsonify({"status": "error", "message": "No GeoJSON provided"}), 400
        
        # Validate GeoJSON structure
        if geo_json.get('type') != 'Feature' or geo_json['geometry']['type'] != 'Polygon':
            return jsonify({
                "status": "error",
                "message": "Only Polygon Feature GeoJSON is supported"
            }), 400
        
        coordinates = geo_json['geometry']['coordinates']
        
        # Create Earth Engine geometry
        ee_geometry = ee.Geometry.Polygon(coordinates)
        
        # Get the most recent image
        image = get_recent_image(ee_geometry)
        
        # Get the thumbnail URL
        image_url = get_image_url(image, ee_geometry)
        
        return jsonify({
            "status": "success",
            "image_url": image_url,
            "bounds": coordinates
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)