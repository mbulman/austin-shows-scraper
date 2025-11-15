import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

URL = "https://austin.showlists.net/"


def read_existing_shows():
    existing_shows = set()
    if os.path.exists("shows.txt"):
        with open("shows.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_shows.add(line)
    return existing_shows


def send_email(new_shows):
    mailgun_api_key = os.environ.get("MAILGUN_API_KEY")
    mailgun_domain = os.environ.get("MAILGUN_DOMAIN")
    from_email = os.environ.get("MAILGUN_FROM_EMAIL")
    to_email = os.environ.get("MAILGUN_TO_EMAIL")
    
    if not all([mailgun_api_key, mailgun_domain, from_email, to_email]):
        print("Mailgun configuration missing. Skipping email notification.")
        return
    
    if not new_shows:
        return
    
    # Format email body
    body_lines = [f"Found {len(new_shows)} new show(s):\n"]
    for show in new_shows:
        body_lines.append(show)
    
    email_body = "\n".join(body_lines)
    
    # Mailgun API endpoint
    url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"
    
    try:
        response = requests.post(
            url,
            auth=("api", mailgun_api_key),
            data={
                "from": from_email,
                "to": to_email,
                "subject": f"New Austin Shows Added ({len(new_shows)} new)",
                "text": email_body
            },
            timeout=30
        )
        response.raise_for_status()
        print(f"Email sent successfully. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")


def scrape():
    # Read existing shows
    existing_shows = read_existing_shows()
    
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

    # Format all shows and find new ones
    all_shows = []
    new_shows = []
    
    for date_str, formatted_date, title, venue, link in results:
        show_line = f"{formatted_date} - {title} @ {venue} - {link}"
        all_shows.append(show_line)
        
        if show_line not in existing_shows:
            new_shows.append(show_line)
    
    # Send email if there are new shows
    if new_shows:
        send_email(new_shows)
    
    # Write all shows to TXT file
    with open("shows.txt", "w", encoding="utf-8") as f:
        for show_line in all_shows:
            f.write(f"{show_line}\n")


if __name__ == "__main__":
    scrape()

