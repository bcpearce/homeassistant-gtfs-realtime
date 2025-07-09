---
name: Feed Request Template
about: Template for requesting additional feeds for feeds.json
title: "[FEED REQUEST]"
labels: ''
assignees: ''

---

Enter information here to help add feeds to `feeds.json`
- Feed Provider Name: 
- Feed Provider URL: <!-- please include the URL to the developer docs for the API, do _not_ include the the main webpage for the transport agency -->

Additional Info
- [ ] This is an update to an existing feed
- [ ] This feed requires signup for authentication (API key, etc.)

Feed data can be tested by adding a `user_feeds.json` file to the `gtfs_realtime` folder on your install. Or by configuring as a custom feed. Feeds added in this file are loaded alongside the public feeds on GitHub.  You can test a feed out beforehand by adding this file and including it there. See `feeds.json` for the format schema. 

- [ ] I have tested the feed using a custom configuration or `user_feeds.json` and confirmed that it works.
