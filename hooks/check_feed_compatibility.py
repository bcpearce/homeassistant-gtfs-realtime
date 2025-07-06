#!/usr/bin/python
"""Script for checking compatibility in `feeds.json`"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from pprint import pprint

from aiohttp import ClientResponseError
from gtfs_station_stop.feed_subject import FeedSubject
from gtfs_station_stop.schedule import async_build_schedule

import re

REPORT_FORMATS = ["md", "dict"]


async def async_test_feed(
    feed_id: str, feed: dict[str, list[str]], headers: list[str]
) -> str:
    """Test a single feed."""
    status = "Failed"
    try:
        for realtime in feed["realtime_feeds"].values():
            subject = FeedSubject([realtime], headers=headers)
            await subject.async_update()
        for static in feed["static_feeds"].values():
            await async_build_schedule(static, headers=headers)
        status = "Success"
    except* ClientResponseError as eg:
        if 401 in [e.status for e in eg.exceptions]:
            status = "Auth Required"
            print(
                f"Failed to authenticate the {feed_id} feed, an authentication header may be required",
                file=sys.stderr,
            )
            for e in eg.exceptions:
                print(f" * {e}", file=sys.stderr)
            if bool(headers):
                print(
                    f"  Headers were provided {headers}, check the credentials and retry",
                    file=sys.stderr,
                )
    except* Exception as eg:
        # fallthrough is failed
        print(f"Exceptions occurred processing feed {feed_id}: ", file=sys.stderr)
        for e in eg.exceptions:
            print(f" * {e}", file=sys.stderr)
        pass
    return status


async def test_feeds(
    feeds: dict[str, list[str]],
    output_format: str = "dict",
    headers_map: dict[str, str] | None = None,
    *,
    sleep_rate_limit: float = 0.0,
) -> dict[str, str]:
    """Test several feeds and report the valid ones."""
    if output_format not in REPORT_FORMATS:
        raise ValueError(
            f"Report type {output_format} is not one of the allowed types in {REPORT_FORMATS}"
        )
    headers_map |= {}
    tasks = {}
    async with asyncio.TaskGroup() as tg:
        for feed_id, feed in feeds.items():
            header_key = ""
            for key in headers_map.keys():
                if re.search(key, feed_id):
                    header_key = key  # only match the first
                    break
            asyncio.sleep(sleep_rate_limit)
            tasks[feed_id] = tg.create_task(
                async_test_feed(feed_id, feed, headers_map.get(header_key, []))
            )

    result = {feed_id: task.result() for feed_id, task in tasks.items()}
    if output_format == "dict":
        pprint(result)
    elif output_format == "md":
        STATUS_DICT = {"Success": "✅", "Failed": "❌", "Auth Required": "🔐"}
        print("# Feed Compatibility")
        print("")
        print("| Feed ID | Status |")
        print("| ------- | ------ |")
        for feed_id, status in result.items():
            print(f"| {feed_id} | {STATUS_DICT.get(status, '❔')} {status} |")

    return result


if __name__ == "__main__":
    filePath = Path(sys.argv[1])

    parser = argparse.ArgumentParser(
        description="Tool for checking validity of the feeds"
    )
    parser.add_argument("input_file", help="Input feed file")
    parser.add_argument(
        "--output-format",
        "-f",
        help=f"Output format for reporting, {REPORT_FORMATS}",
        default="dict",
    )
    parser.add_argument(
        "--auth-header",
        "-a",
        metavar="KEY=VALUE",
        nargs="*",
        help="Additional headers to include when making feed requests, should be in the form of <feed_id>='<header>'",
        default=None,
    )
    parser.add_argument(
        "--sleep-rate-limit",
        "-s",
        help="Sleep time between queuing tasks to help stay under API limits",
        type=float,
        default=0.0,
    )
    args = parser.parse_args()

    auth: dict[str, dict[str, str]] = {}
    for feed_id_to_auth_header in args.auth_header or []:
        feed_id, auth_header = feed_id_to_auth_header.split("=")
        header_key, header_value = (x.strip() for x in auth_header.split(":"))
        auth[feed_id] = {header_key: header_value}

    with open(filePath, "rb") as json_f:
        feeds = json.load(json_f)

    asyncio.run(
        test_feeds(
            feeds, args.output_format, auth, sleep_rate_limit=args.sleep_rate_limit
        )
    )
