#!/usr/bin/python
"""Script for checking compatibility in `feeds.json`"""

from aiohttp import ClientResponseError
from gtfs_station_stop.feed_subject import FeedSubject
from gtfs_station_stop.schedule import async_build_schedule
import json
import sys
from pathlib import Path
import asyncio
from pprint import pprint
import argparse

REPORT_FORMATS = ["md", "dict"]


async def async_test_feed(feed: dict[str, list[str]]) -> str:
    """Test a single feed."""
    status = "Failed"
    try:
        for realtime in feed["realtime_feeds"].values():
            subject = FeedSubject([realtime])
            await subject.async_update()
        for static in feed["static_feeds"].values():
            await async_build_schedule(static)
        status = "Success"
    except* ClientResponseError as eg:
        if 401 in [e.status for e in eg.exceptions]:
            status = "Auth Required"
    return status


async def test_feeds(
    feeds: dict[str, list[str]], output_format: str = "dict"
) -> dict[str, str]:
    """Test several feeds and report the valid ones."""
    if output_format not in REPORT_FORMATS:
        raise ValueError(
            f"Report type {output_format} is not one of the allowed types in {REPORT_FORMATS}"
        )
    tasks = {}
    async with asyncio.TaskGroup() as tg:
        for feed_id, feed in feeds.items():
            tasks[feed_id] = tg.create_task(async_test_feed(feed))

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
    args = parser.parse_args()

    with open(filePath, "rb") as json_f:
        feeds = json.load(json_f)

    asyncio.run(test_feeds(feeds, args.output_format))
