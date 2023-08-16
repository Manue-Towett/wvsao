from bs4 import BeautifulSoup


with open("item.html", "r") as file:
    html = file.read()

soup = BeautifulSoup(html, "html.parser")

payload = {}

for field in soup.select("input"):
    try:
        payload[field["name"]] = field["value"]
    except:pass

import json

with open("payload.json", "w") as file:
    json.dump(payload, file, indent=4)