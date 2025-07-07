#!/usr/bin/python
"""Script for checking compatibility in `feeds.json`"""

import argparse
import asyncio
import json
import re
import sys
import tqdm
from pathlib import Path
from pprint import pprint

from aiohttp import ClientResponseError
from gtfs_station_stop.feed_subject import FeedSubject
from gtfs_station_stop.schedule import async_build_schedule


REPORT_FORMATS = ["md", "dict"]
STATUS_DICT = {
    "Success": "✅",
    "Failed": "❌",
    "Auth Provided": "🔓",
    "Auth Missing": "🔐",
    "Unsure": "❔",
}

URL_PARAM_PLACEHOLDERS = ["[ApiKey]"]


def _repr_without_query(e: ClientResponseError) -> str:
    """Similar to str(e), but without query string which may contain sensitive params."""
    url = e.request_info.url.with_query(None)
    return f"{e.status}, message={e.message}, {url} (query may be hidden)"


def _replace_placeholders(s: str) -> str:
    """Replace user-friendly placeholders in feeds.json with a python-formattable brace."""
    tmp = s
    for i, ph in enumerate(URL_PARAM_PLACEHOLDERS):
        tmp = tmp.replace(ph, f"{{{i}}}")
    return tmp


async def async_test_feed(
    feed_id: str,
    feed: dict[str, list[str]],
    headers: dict[str, str] | None,
    params: list[str] | None,
) -> tuple[str, str]:
    """Test a single feed."""
    if params is None:
        params = []
    status = "Failed"
    notice = ""
    try:
        for realtime in feed["realtime_feeds"].values():
            rt = _replace_placeholders(realtime)
            subject = FeedSubject([rt.format(*params)], headers=headers)
            await subject.async_update()
        for static in feed["static_feeds"].values():
            st = _replace_placeholders(static)
            await async_build_schedule(st.format(*params), headers=headers)
        status = "Success"
        if headers:
            notice = "Auth Provided"
    except* ClientResponseError as eg:
        status_codes = [e.status for e in eg.exceptions]
        notice = ",".join(f"{e.status}: {e.message}" for e in eg.exceptions)
        status = "Failed"
        if any(sc in status_codes for sc in [401, 403]):
            print(
                f"Failed to authenticate the {feed_id} feed, an authentication header may be required",
                file=sys.stderr,
            )
            for e in eg.exceptions:
                print(f" * {_repr_without_query(e)}", file=sys.stderr)
            if bool(headers):
                print(
                    " * Headers were provided, check the credentials and retry",
                    file=sys.stderr,
                )
        elif 429 in status_codes:
            notice = "API Limit Exceeded"
            status = "Unsure"
        else:
            print(f"Exceptions occurred processing feed {feed_id}: ", file=sys.stderr)
            for e in eg.exceptions:
                print(
                    f" * {_repr_without_query(e)}",
                    file=sys.stderr,
                )
    except* IndexError:
        print(f"Index error, {feed_id} requires a URL param that was not provided")
        notice = "Missing URL parameter"
    except* Exception as eg:
        # fallthrough is failed
        print(f"Exceptions occurred processing feed {feed_id}: ", file=sys.stderr)
        for e in eg.exceptions:
            print(f" * {e}", file=sys.stderr)
    return status, notice


async def test_feeds(
    feeds: dict[str, list[str]],
    output_format: str = "dict",
    headers_map: dict[str, dict[str, str]] | None = None,
    params_map: dict[str, list[str]] | None = None,
    *,
    sleep_rate_limit: float = 0.0,
) -> dict[str, str]:
    """Test several feeds and report the valid ones."""
    if output_format not in REPORT_FORMATS:
        raise ValueError(
            f"Report type {output_format} is not one of the allowed types in {REPORT_FORMATS}"
        )
    headers_map |= {}
    params_map |= {}
    results = {}
    meter = tqdm.tqdm(feeds.items())
    for feed_id, feed in meter:
        meter.set_description(f"Verifying {feed['name']}")
        header_key = ""
        for key in headers_map.keys():
            if re.search(key, feed_id):
                header_key = key  # only match the first
                break
        params_key = ""
        for key in params_map.keys():
            if re.search(key, feed_id):
                params_key = key  # only match the first
                break
        await asyncio.sleep(sleep_rate_limit)
        results[feed_id] = await async_test_feed(
            feed_id, feed, headers_map.get(header_key), params_map.get(params_key)
        )

    if output_format == "dict":
        pprint(results)
    elif output_format == "md":
        print("# Feed Compatibility")
        print("")
        print("| Feed ID | Name | Status | Details |")
        print("| ------- | ---- | ------ | ------- |")
        for feed_id, status in results.items():
            print(
                f"| {feed_id} | {feeds[feed_id]['name']} | {STATUS_DICT.get(status[0], '❔')} {status[0]} | {STATUS_DICT.get(status[1], '')} {status[1]} |"
            )

    return results


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
        help="Additional headers to include when making feed requests, should be in the form of <feed_id_regex>='<header>'",
        default=None,
    )
    parser.add_argument(
        "--url-param",
        "-u",
        metavar="KEY=VALUE",
        nargs="*",
        help="""
        URL parameters to include when making feed requests, should be in the form <feed_id_regex>='<parameter>'
        The parameter will 
        """,
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
    params: dict[str, list[str]] = {}
    for feed_id_to_auth_header in args.auth_header or []:
        feed_id, auth_header = feed_id_to_auth_header.split("=")
        header_key, header_value = (x.strip() for x in auth_header.split(":"))
        auth[feed_id] = {header_key: header_value}

    for feed_id_to_url_param in args.url_param or []:
        feed_id, url_param = feed_id_to_url_param.split("=")
        params[feed_id] = [url_param.strip()]

    with open(filePath, "rb") as json_f:
        feeds = json.load(json_f)

    asyncio.run(
        test_feeds(
            feeds,
            args.output_format,
            auth,
            params,
            sleep_rate_limit=args.sleep_rate_limit,
        )
    )
