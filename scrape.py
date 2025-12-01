import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import sys

URL = "https://austin.showlists.net/"


def parse_recipients(raw_value):
    """Split comma-delimited recipient string into a list of emails."""
    recipients = [email.strip() for email in raw_value.split(",") if email.strip()]
    if not recipients:
        print("Error: MAILGUN_TO_EMAIL must contain at least one recipient address")
        sys.exit(1)
    return recipients


def check_email_config():
    """Check if email configuration is present. Exit if missing."""
    mailgun_api_key = os.environ.get("MAILGUN_API_KEY")
    mailgun_domain = os.environ.get("MAILGUN_DOMAIN")
    from_email = os.environ.get("MAILGUN_FROM_EMAIL")
    to_email = os.environ.get("MAILGUN_TO_EMAIL")
    
    missing = []
    if not mailgun_api_key:
        missing.append("MAILGUN_API_KEY")
    if not mailgun_domain:
        missing.append("MAILGUN_DOMAIN")
    if not from_email:
        missing.append("MAILGUN_FROM_EMAIL")
    if not to_email:
        missing.append("MAILGUN_TO_EMAIL")
    
    if missing:
        print(f"Error: Missing required email configuration: {', '.join(missing)}")
        sys.exit(1)
    
    recipients = parse_recipients(to_email)
    
    return mailgun_api_key, mailgun_domain, from_email, recipients


def read_existing_shows():
    existing_shows = set()
    if os.path.exists("shows.txt"):
        with open("shows.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_shows.add(line)
    return existing_shows


def send_email(new_shows_data, mailgun_api_key, mailgun_domain, from_email, to_emails):
    
    if not new_shows_data:
        return
    
    # Format HTML email body
    html_lines = [f"<p>Found {len(new_shows_data)} new show(s):</p>"]
    for date_str, formatted_date, title, venue, link in new_shows_data:
        # Make title a bold hyperlink, remove raw link text
        title_link = f'<b><a href="{link}">{title}</a></b>'
        html_lines.append(f"<p>{formatted_date} - {title_link} @ {venue}</p>")
    
    html_body = "\n".join(html_lines)
    
    # Mailgun API endpoint
    url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"

    print(f"Sending email to {to_emails}##")
    
    response = requests.post(
        url,
        auth=("api", mailgun_api_key),
        data={
            "from": from_email,
            "to": to_emails,
            "subject": f"New Austin Shows Added ({len(new_shows_data)} new)",
            "html": html_body
        },
        timeout=30
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            try:
                body = exc.response.text.strip()
            except Exception:
                body = "<unable to read response body>"
        print(f"Mailgun API error: {exc}. Response body: {body}")
        raise
    else:
        print(f"Email sent successfully. Status code: {response.status_code}")


def scrape():
    # Check email configuration first - fail early if missing
    mailgun_api_key, mailgun_domain, from_email, to_emails = check_email_config()
    
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

            # Exclude things we won't tend to care about
            if venue in ["Elephant Room", "Sagebrush", "C-Boy’s Heart & Soul"]:
                continue

            results.append([date_str, formatted_date, title, venue, link])

    # Sort by date, then title
    results.sort(key=lambda row: (row[0], row[2]))

    # Format all shows and find new ones
    all_shows = []
    new_shows_data = []
    
    for date_str, formatted_date, title, venue, link in results:
        # Remove link from show_line format
        show_line = f"{formatted_date} - {title} @ {venue}"
        all_shows.append(show_line)
        
        if show_line not in existing_shows:
            new_shows_data.append([date_str, formatted_date, title, venue, link])
    
    # Send email if there are new shows
    if new_shows_data:
        send_email(new_shows_data, mailgun_api_key, mailgun_domain, from_email, to_emails)
    
    # Write all shows to TXT file (only if we got this far without errors)
    with open("shows.txt", "w", encoding="utf-8") as f:
        for show_line in all_shows:
            f.write(f"{show_line}\n")


if __name__ == "__main__":
    scrape()

