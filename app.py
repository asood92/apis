import os
import requests

from pprint import PrettyPrinter
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file
from geopy.geocoders import Nominatim


################################################################################
## SETUP
################################################################################

app = Flask(__name__)

# Get the API key from the '.env' file
load_dotenv()
API_KEY = os.getenv("API_KEY")

pp = PrettyPrinter(indent=4)


################################################################################
## ROUTES
################################################################################


@app.route("/")
def home():
    """Displays the homepage with forms for current or historical data."""
    context = {
        "min_date": (datetime.now() - timedelta(days=5)),
        "max_date": datetime.now(),
    }
    return render_template("home.html", **context)


def get_letter_for_units(units):
    """Returns a shorthand letter for the given units."""
    return "F" if units == "imperial" else "C" if units == "metric" else "K"


@app.route("/results")
def results():
    """Displays results for current weather conditions."""
    city = request.args.get("city")
    units = request.args.get("units")

    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "appid": API_KEY,
        "q": city,
        "units": units,
    }

    result_json = requests.get(url, params=params).json()

    pp.pprint(result_json)

    context = {
        "date": datetime.now(),
        "city": city,
        "description": result_json["weather"][0]["description"],
        "temp": result_json["main"]["temp"],
        "humidity": result_json["main"]["humidity"],
        "wind_speed": result_json["wind"]["speed"],
        "sunrise": datetime.fromtimestamp(result_json["sys"]["sunrise"]),
        "sunset": datetime.fromtimestamp(result_json["sys"]["sunset"]),
        "units_letter": get_letter_for_units(units),
    }

    return render_template("results.html", **context)


def get_min_temp(results):
    # Not sure how to actually do this given the API says:
    #
    # In 5 day / 3 hour forecast API, Hourly forecast API and Current weather API - temp_min and temp_max are optional parameters mean min / max temperature in the city at the current moment just for your reference. For large cities and megalopolises geographically expanded it might be applicable. In most cases both temp_min and temp_max parameters have the same volume as 'temp'. Please, use temp_min and temp_max parameters in current weather API optionally.
    #
    # So it looks like it should just return the same temperature for min and max in current hourly objects. Which it does, but I'm reading that you can only get the proper min max in the 16 day forecast - or with the PAID API.

    """Returns the minimum temp for the given hourly weather objects."""
    return min(results, key=lambda hr_weather: hr_weather["temp"])["temp"]


def get_max_temp(results):
    """Returns the maximum temp for the given hourly weather objects."""
    # Reference lines 79-81
    return max(results, key=lambda hr_weather: hr_weather["temp"])["temp"]


def get_lat_lon(city_name):
    geolocator = Nominatim(user_agent="Weather Application")
    location = geolocator.geocode(city_name)
    if location is not None:
        return location.latitude, location.longitude
    return 0, 0


@app.route("/historical_results")
def historical_results():
    """Displays historical weather forecast for a given day."""
    city = request.args.get("city")
    date = request.args.get("date")
    units = request.args.get("units")
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    date_in_seconds = date_obj.strftime("%s")

    latitude, longitude = get_lat_lon(city)

    url = "http://api.openweathermap.org/data/2.5/onecall/timemachine"
    params = {
        "appid": API_KEY,
        "lat": latitude,
        "lon": longitude,
        "units": units,
        "dt": date_in_seconds,
    }

    result_json = requests.get(url, params=params).json()

    pp.pprint(result_json)

    result_current = result_json["current"]
    result_hourly = result_json["hourly"]

    context = {
        "city": city,
        "date": date_obj,
        "lat": latitude,
        "lon": longitude,
        "units": units,
        "units_letter": get_letter_for_units(units),
        "description": result_current["weather"][0]["description"],
        "temp": result_current["temp"],
        "min_temp": get_min_temp(result_hourly),
        "max_temp": get_max_temp(result_hourly),
    }

    return render_template("historical_results.html", **context)


if __name__ == "__main__":
    app.run(debug=True)