from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

WIKI_API = "https://jpuffle5-boomerang-archives.fandom.com/api.php"

CHANNEL_ID = "boomerang-classic-jpuffle5"
CHANNEL_NAME = "Boomerang Classic"
CHANNEL_LOGO = "http://drewlive2423.duckdns.org:9000/Logos/Boomerang.png"

# User preference: Central time / Chicago.
SCHEDULE_TIMEZONE = "America/Chicago"

# Generate the next 48 hours of guide data.
HOURS_AHEAD = 48


def date_to_page_title(date_obj):
    return f"{date_obj.strftime('%B')} {date_obj.day}, {date_obj.year}"


def get_page_html(title):
    params = {
        "action": "parse",
        "page": title,
        "format": "json",
        "prop": "text",
        "redirects": "1",
    }

    headers = {
        "User-Agent": "boomerang-classic-epg-builder/1.0"
    }

    response = requests.get(WIKI_API, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        return ""

    return data["parse"]["text"]["*"]


def parse_time_to_24_hour(time_text):
    cleaned = time_text.strip().lower().replace(" ", "")
    match = re.match(r"^(\d{1,2}):(\d{2})(am|pm)$", cleaned)

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    ampm = match.group(3)

    if ampm == "am" and hour == 12:
        hour = 0
    elif ampm == "pm" and hour != 12:
        hour += 12

    return hour, minute


def get_schedule_rows_for_date(date_obj):
    timezone = ZoneInfo(SCHEDULE_TIMEZONE)
    title = date_to_page_title(date_obj)
    page_html = get_page_html(title)

    if not page_html:
        return []

    soup = BeautifulSoup(page_html, "html.parser")
    rows = []

    last_show = ""
    last_episode = ""

    for table in soup.find_all("table"):
        header_text = table.get_text(" ", strip=True).lower()

        if "time" not in header_text or "show" not in header_text:
            continue

        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]

            if len(cells) < 2:
                continue

            if cells[0].strip().lower() == "time":
                continue

            parsed_time = parse_time_to_24_hour(cells[0])

            if parsed_time is None:
                continue

            hour, minute = parsed_time

            show = cells[1].strip() if len(cells) > 1 else ""
            episode = cells[2].strip() if len(cells) > 2 else ""

            # Some long movies/specials may have blank continuation rows.
            # This keeps the same title going until the next filled-in title appears.
            if show:
                last_show = show
                last_episode = episode
            else:
                show = last_show
                episode = last_episode

            if not show:
                continue

            start_time = datetime(
                date_obj.year,
                date_obj.month,
                date_obj.day,
                hour,
                minute,
                tzinfo=timezone,
            )

            rows.append({
                "start": start_time,
                "show": show,
                "episode": episode,
            })

    return rows


def xmltv_datetime(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")


def build_epg():
    timezone = ZoneInfo(SCHEDULE_TIMEZONE)
    now = datetime.now(timezone)
    window_end = now + timedelta(hours=HOURS_AHEAD)

    all_rows = []

    # Pull today plus the next 3 days so the next 48 hours are covered.
    for day_offset in range(0, 4):
        date_obj = (now + timedelta(days=day_offset)).date()
        all_rows.extend(get_schedule_rows_for_date(date_obj))

    all_rows.sort(key=lambda row: row["start"])

    tv = ET.Element("tv", {
        "generator-info-name": "jpuffle5-boomerang-fandom-epg"
    })

    channel = ET.SubElement(tv, "channel", {"id": CHANNEL_ID})
    ET.SubElement(channel, "display-name").text = CHANNEL_NAME
    ET.SubElement(channel, "icon", {"src": CHANNEL_LOGO})

    for index, row in enumerate(all_rows):
        start = row["start"]

        if index + 1 < len(all_rows):
            stop = all_rows[index + 1]["start"]
        else:
            stop = start + timedelta(minutes=30)

        if stop <= now:
            continue

        if start >= window_end:
            continue

        if stop > window_end:
            stop = window_end

        programme = ET.SubElement(tv, "programme", {
            "start": xmltv_datetime(start),
            "stop": xmltv_datetime(stop),
            "channel": CHANNEL_ID,
        })

        ET.SubElement(programme, "title", {"lang": "en"}).text = row["show"]

        if row["episode"]:
            ET.SubElement(programme, "sub-title", {"lang": "en"}).text = row["episode"]
            ET.SubElement(programme, "desc", {"lang": "en"}).text = row["episode"]

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ", level=0)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    build_epg()
