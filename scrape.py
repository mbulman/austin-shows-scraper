import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://austin.showlists.net/"

def scrape():
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    # Each date block looks like:
    # <div class="show-date" id="20250115"> ... </div>
    for date_div in soup.select('div.show-date'):
        date_str = date_div.get("id")  # YYYYMMDD
        # Convert YYYYMMDD to "Sat Nov 15" format
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        formatted_date = date_obj.strftime("%a %b %d")

        # for each show listing inside this date block:
        for li in date_div.select("li"):
            anchors = li.find_all("a")
            if not anchors:
                continue

            # Find title and venue from separate anchor tags
            title = ""
            venue = ""
            link = ""
            
            for a in anchors:
                if a.get("data-show-title"):
                    title = a.get("data-show-title", "").strip()
                    link = a.get("href", "").strip()
                # Check if this anchor has "venue-title" in its classes
                if a.get("class") and "venue-title" in a.get("class"):
                    venue = a.get_text(strip=True)

            if not title:
                continue

            results.append([date_str, formatted_date, title, venue, link])

    # Sort by date, then title
    results.sort(key=lambda row: (row[0], row[2]))

    # Write TXT file
    with open("shows.txt", "w", encoding="utf-8") as f:
        for date_str, formatted_date, title, venue, link in results:
            f.write(f"{formatted_date} - {title} @ {venue} - {link}\n")


if __name__ == "__main__":
    scrape()

