# How to Contribute to this Repository

## Bugs

If you found a bug, please report it on the [Issues](https://github.com/bcpearce/homeassistant-gtfs-realtime/issues) page. 

**This feed isn't working**

While GTFS stands for *General* Transit Feed Specification, there is much variation in the way that a specific provider may configure their feeds. This repository tries to keep a number of feed specs up to date both to confirm compatibility with various providers, and for convenience in setting up the integration in Home Assistant. 

- *Check your Authentication* 
  - some feeds require authentication, others do not. If the provider requires an authentication headers, make sure it is formatted exactly as that provider requires. For some providers a "hint" is given in the setup that has a header name and a placeholder for an API Key or Token. 
  - Make sure you do not accidentally post your token or API key when reporting an issue. 
- *Check if a feed can be downloaded manually* 
  - "static" data (representing the transit schedules and other data) is periodically updated by the provider.  It is generally provided as a .zip file with a number of .txt files with comma separated "data sets". These are updated at a regular interval that may be days, weeks, months, or--less commonly--hours. Sometimes the feed specification may become unavailable or corrupted. **This type of issue cannot be resolved by the repository owner**. 
  - "realtime" data (representing trip updates or service alerts) is also updated regularly, but is generally done minute-to-minute. These are provided as protobufs, which may require some additional software to decode as they are not human readable. 
- *A feed's URLs have moved* 
  - you can report this as a bug or open a pull request with the updated data. 

Feeds are checked daily in a GitHub Actions Workflow. You can check the most recent run to see if a given feed is experiencing errors. 

[![Check GTFS Feed Compatibility](https://github.com/bcpearce/homeassistant-gtfs-realtime/actions/workflows/feed_compatibility.yaml/badge.svg)](https://github.com/bcpearce/homeassistant-gtfs-realtime/actions/workflows/feed_compatibility.yaml)

**Other Bugs**

This project relies on [gtfs-station-stop](https://github.com/bcpearce/gtfs-station-stop) for grabbing and formatting data feeds into an "arrival clock" style that can be used in Home Assistant. This is consistent with the [Home Assistant Developer Documentation](https://developers.home-assistant.io/docs/creating_platform_index#interfacing-with-devices) recommendations, however it can make bug reporting slightly more complex as it may need to be fixed in the underlying Python library. Note that issues reported for bugs in this integration may be solved with updates to the underlying data provider library instead. 

## Features

**Adding feeds**

If you have a custom feed that works with this repository, feel free to open a pull request adding it to help out any other users. See [feeds.json](/custom_components/gtfs_realtime/feeds.json) for the schema. 
- If authentication is required, provide an `auth_hint` or placeholder in the URL. 
- Make sure to include relevant static *and* realtime feed URLs. 
- Include a link to the Terms and Conditions for a provider in the `disclaimer` field. 

The [feeds.json](/custom_components/gtfs_realtime/feeds.json) file will be autoformatted by [pre-commit.ci](https://pre-commit.ci/) and a GitHub Actions Workflow will test to ensure the new additions do not break the config flow. 

When testing a new feed, you can add it in a separate file added into the `gtfs_realtime` folder named `user_feeds.json` which is also read during config flow. 

If available, and allowed by the feed provider's licensing, icons can also be included in the [resources/](resources/) folder to improve arrival visuals. 