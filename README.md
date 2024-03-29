
![GTFS Realtime](resources/logo.svg)
# GTFS Realtime for Home Assistant

## Installation

This integration can be installed manually or through [HACS](https://hacs.xyz/) as a custom repository.

#### Manual

Copy files in [custom_components/gtfs_realtime](custom_components/gtfs_realtime/) to [/path/to/homeassistant/config/custom_components/gtfs_realtime](#).

#### HACS

1. Go to HACS in your Home Assistant Integration
2. Select "Integrations"
3. Click the "..." in the upper left corner.
4. Go to Custom Repositories
5. Add this repository's URL https://github.com/bcpearce/homeassistant-gtfs-realtime in "Repository", and set the category to "Integration"

## Configuration

Configuration is currently supported only through [configuration.yaml]().

An example configuration file is provided in [example/configuration.yaml](example/configuration.yaml).

### Static GTFS Data

Static GTFS data is provided as a .zip file containing a number of .txt files representing a relational database.
The file can either specify a URL from the GTFS service provider, and it will be re-downloaded every day, or it can be a local file. 

GTFS static info does not change as rapidly as realtime data, but will need to be refreshed.  For accurate headsigns and trip metadata, it is best to specify the provider's URL

```
gtfs_realtime:
  api_key: !secret gtfs_realtime_api_key
  url_endpoints:
   - "https://gtfs.example.com/feed1"
   - "https://gtfs.example.com/feed2"
   - "https://gtfs.example.com/alerts"
  gtfs_static_data: 
   - "https://gtfs.example.com/static.zip"
   - "https://gtfs.example.com/static_supplemented.zip"
```

### Feed URLs

A list of feed URLs should be provided.

### API Key

If your provider requires an API Key, include it under `gtfs_realtime.api_key`. It is recommended to use the `secrets.yaml` file to store it and reference it with `!secret`. 

### New York City Subway Data

A sample configuration for New York City Subways is provided in [example/nyct_configuration.yaml](example/nyct_configuration.yaml).

Obtain an API key [here](https://api.mta.info/)

#### Resources

The [resources/NYCT_Bullets](resources/NYCT_Bullets/) folder contains ready-to-use SVG files for customizing arrival icons provided by Wikimedia Commons.

### Other Transit Systems

This software may work for other GTFS realtime providers, but has not been tested. 

## Frontend

Example frontend card configs can be found in [example/fontend.yaml](example/frontend.yaml).

## Sensors

### Arrival Sensor

The number of sensors can be specified with the `sensor.arrival_limit` key in the yaml configuration. By default this is 4.  

Sensors will indicate the 1st, 2nd, 3rd, ... etc. arrivals for a given `stop_id` ordered by shortest time.  If no scheduled trips exist for a given arrival ordinal, it will take on the state "Unknown". That is to say, the first sensor will always have the shortest time to arrival, the second sensor will have the second shortest time to arrival, and so on. 

Raw sensor data is provided in seconds. Minutes are the recommended unit.

### Alert Sensor

Alert sensors can be setup for either a `stop_id` or a `route_id`. The [example/frontend.yaml](example/frontend.yaml) file shows how to set up conditional cards that display only if an alert is active. The alert sensor will switch to the "Problem" state if an alert is active for a given station or route. This can be used in automations, such as turning on an indicator LED when an alert becomes active. 

## GTFS Station Stop

This package utilizes [GTFS Station Stop](https://pypi.org/project/gtfs-station-stop/) to provide updates to Home Assistant sensors. 

## Disclaimer

This software is not developed with or affiliated with Home Assistant or with any GTFS API provider. It is not guaranteed to work, use at your own risk. 
