from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


WIKI_API = "https://jpuffle5-boomerang-archives.fandom.com/api.php"

CHANNEL_ID = "boomerang-classic-jpuffle5"
CHANNEL_NAME = "Boomerang Classic"
CHANNEL_ICON = "http://drewlive2423.duckdns.org:9000/Logos/Boomerang.png"
EPG_URL = "https://cjrudermedia-1.github.io/boomerang-classic-epg/epg.xml"

SCHEDULE_TIMEZONE = "America/Chicago"

# TiviMate is currently showing the generated guide two hours ahead.
# The previous value was +1. Changing this to -1 moves the output back by 2 hours.
EPG_TIME_SHIFT_HOURS = -1

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
        "User-Agent": "boomerang-classic-epg-builder/1.1"
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


def extract_table_grid(table):
    """
    Return a list of rows with rowspan and colspan expanded.

    Fandom schedule tables sometimes use rowspans for the Show column.
    Without expanding those rowspans, continuation rows can shift left and
    the episode text can be mistaken for the show title.
    """
    grid = []
    active_rowspans = {}

    for tr in table.find_all("tr"):
        row = []
        col_index = 0
        cells = tr.find_all(["td", "th"])

        for cell in cells:
            while col_index in active_rowspans:
                span = active_rowspans[col_index]
                row.append(span["text"])
                span["rows_left"] -= 1

                if span["rows_left"] <= 0:
                    del active_rowspans[col_index]

                col_index += 1

            text = cell.get_text(" ", strip=True)
            rowspan = int(cell.get("rowspan", 1) or 1)
            colspan = int(cell.get("colspan", 1) or 1)

            for offset in range(colspan):
                row.append(text)

                if rowspan > 1:
                    active_rowspans[col_index + offset] = {
                        "rows_left": rowspan - 1,
                        "text": text,
                    }

            col_index += colspan

        while col_index in active_rowspans:
            span = active_rowspans[col_index]
            row.append(span["text"])
            span["rows_left"] -= 1

            if span["rows_left"] <= 0:
                del active_rowspans[col_index]

            col_index += 1

        if row:
            grid.append(row)

    return grid


def get_schedule_rows_for_date(date_obj):
    timezone = ZoneInfo(SCHEDULE_TIMEZONE)
    title = date_to_page_title(date_obj)
    page_html = get_page_html(title)

    if not page_html:
        return []

    soup = BeautifulSoup(page_html, "html.parser")
    rows = []

    for table in soup.find_all("table"):
        header_text = table.get_text(" ", strip=True).lower()

        if "time" not in header_text or "show" not in header_text:
            continue

        grid = extract_table_grid(table)

        for row in grid:
            if len(row) < 2:
                continue

            if row[0].strip().lower() == "time":
                continue

            parsed_time = parse_time_to_24_hour(row[0])

            if parsed_time is None:
                continue

            show = row[1].strip() if len(row) > 1 else ""
            episode = row[2].strip() if len(row) > 2 else ""

            if not show:
                continue

            hour, minute = parsed_time

            start_time = datetime(
                date_obj.year,
                date_obj.month,
                date_obj.day,
                hour,
                minute,
                tzinfo=timezone,
            ) + timedelta(hours=EPG_TIME_SHIFT_HOURS)

            rows.append({
                "start": start_time,
                "show": show,
                "episode": episode,
            })

    return rows


def merge_repeated_blocks(rows):
    """
    Merge adjacent identical rows.

    This keeps long movies from showing as several separate 30-minute entries
    when the site repeats the same title through a rowspan. It does not merge
    continuation episodes because those have different subtitles.
    """
    merged = []

    for row in rows:
        if (
            merged
            and row["show"] == merged[-1]["show"]
            and row["episode"] == merged[-1]["episode"]
        ):
            continue

        merged.append(row)

    return merged


def xmltv_datetime(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")


def build_epg():
    timezone = ZoneInfo(SCHEDULE_TIMEZONE)
    now = datetime.now(timezone)
    window_end = now + timedelta(hours=HOURS_AHEAD)

    all_rows = []

    # Pull yesterday through the next 4 days so shifted times around midnight are covered.
    for day_offset in range(-1, 5):
        date_obj = (now + timedelta(days=day_offset)).date()
        all_rows.extend(get_schedule_rows_for_date(date_obj))

    all_rows.sort(key=lambda row: row["start"])
    all_rows = merge_repeated_blocks(all_rows)

    tv = ET.Element("tv", {
        "generator-info-name": "jpuffle5-boomerang-fandom-epg",
        "generator-info-url": EPG_URL,
    })

    channel = ET.SubElement(tv, "channel", {"id": CHANNEL_ID})
    ET.SubElement(channel, "display-name").text = CHANNEL_NAME
    ET.SubElement(channel, "icon", {"src": CHANNEL_ICON})

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
