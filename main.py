import re
import sys
import json
import time
import random
import threading
import configparser
from typing import Optional
from urllib.parse import urlencode

import requests
import pandas as pd
from requests import Response
from bs4 import BeautifulSoup

from utils import Logger

BASE_URL = "https://land.wvsao.gov{}"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://land.wvsao.gov",
    # "Referer": "https://land.wvsao.gov/Default?ReturnUrl=%2fportal%2fBUYER%2fDefault",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 OPR/101.0.0.0"
}

UPDATE = {
    "__EVENTTARGET": "",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": "",
    "__VIEWSTATEGENERATOR": "BE651B89",
    "__SCROLLPOSITIONX": "0",
    "__SCROLLPOSITIONY": "905",
    "__VIEWSTATEENCRYPTED": "",
    "__PREVIOUSPAGE": "",
    "__EVENTVALIDATION": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$tbBillName": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$tbBillAddr1": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$tbBillAddr2": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$tbBillCity": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$ddlState": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$tbBillZip": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$tbAttorneyFees": "500",
    "ctl00$MainContent_FullWidth$dvNTRHeader$Button1": "Update",
}

UPDATE_BTN = {
    "__EVENTTARGET": "",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": "",
    "__VIEWSTATEGENERATOR": "BE651B89",
    "__SCROLLPOSITIONX": "0",
    "__SCROLLPOSITIONY": "0",
    "__VIEWSTATEENCRYPTED": "",
    "__PREVIOUSPAGE": "",
    "__EVENTVALIDATION": "",
    "ctl00$MainContent_FullWidth$dvNTRHeader$btnUpdateBilling": "Update NTR Info"
}

CONFIG = configparser.ConfigParser()

with open("./settings/settings.ini", "r") as file:
    CONFIG.read_file(file)

USERNAME = CONFIG.get("credentials", "username")

PASSWORD = CONFIG.get("credentials", "password")

CSV_FILE_PATH = CONFIG.get("input", "csv_path")

class AttorneyFeeUpdater:
    """Updates the attorney's fee in https://land.wvsao.gov"""
    def __init__(self) -> None:
        self.logger = Logger(__class__.__name__)
        self.logger.info("*****Attorney Fee Updater started*****")

        self.queue = []
        self.updated = []
        self.crawled = []
        self.proxies = []
        self.properties = {}

        self.cert_list = self.__read_csv()

        threading.Thread(target=self.fetch_proxies, daemon=True).start()
    
    def __login(self) -> tuple[requests.Session, dict[str, str]]:
        """Logs into https://land.wvsao.gov"""
        while not len(self.proxies):pass

        while True:
            try:
                self.logger.info("Logging into wvsao...")

                session = requests.Session()

                proxy = random.choice(self.proxies)

                response = session.get(BASE_URL.format("/Default"), 
                                       headers=HEADERS,
                                       proxies={"http": proxy,
                                                "https": proxy},
                                    timeout=10,
                                    verify=False)
                
                if not response.ok: continue

                soup = BeautifulSoup(response.text, "html.parser")

                form = soup.select_one("form#form1")

                if form is None: continue

                self.logger.info("Init success...")
                    
                payload = {}

                for field in form.select("input"):
                    try:
                        payload[field["name"]] = field["value"]
                    except:pass
                
                user = {"ctl00$MainContent$landLogin$UserName": "pivotcapital@lmxmail.com",
                        "ctl00$MainContent$landLogin$Password": "G!4H$d!mDF&Rge23"}
                
                payload.update(user)

                params = {"ReturnUrl": "/portal/BUYER/"}

                response = session.post(BASE_URL.format("/Default"),
                                        headers=HEADERS,
                                        proxies={"http": proxy,
                                                 "https": proxy},
                                        verify=False,
                                        data=urlencode(payload),
                                        params=params)
                
                if response.ok:
                    self.logger.info("Login success...")

                    self.__extract_properties(response)

                    self.logger.info(f"Properties found on wvsao: {len(self.properties)}")

                    payload = self.__extract_payload(response)

                    self.proxy = proxy
                    
                    return session, payload

            except: self.logger.error("")
    
    def __read_csv(self) -> list[dict[str, str]]:
        """Reads the input csv file containing cert numbers"""
        self.logger.info("Reading csv file...")

        try:
            df = pd.read_csv(CSV_FILE_PATH)
        except:
            self.logger.error("FATAL ERROR! CSV file not found.")

            sys.exit(1)
        
        unique_df = df.dropna().drop_duplicates()

        cert_list = unique_df.to_dict("records")

        self.logger.info("Properties found in csv: {}".format(len(cert_list)))

        return cert_list
    
    def fetch_proxies(self) -> None:
        """Fetches proxies to be used"""
        while True:
            try:
                # self.logger.info("here")
                response = requests.get("https://sslproxies.org/")

                soup = BeautifulSoup(response.text, "html.parser")

                for row in soup.select("table tbody tr"):
                    try:
                        if row.select("td")[2].get_text(strip=True) != "US":
                            continue

                        self.proxies.append("http://{}:{}".format(
                            row.select("td")[0].get_text(strip=True),
                            row.select("td")[1].get_text(strip=True)
                        ))
                    except:pass
            except: self.logger.error("")

            self.proxies = list(set(self.proxies))

            # self.logger.info("Proxies found: {}".format(len(self.proxies)))

            time.sleep(5)
    
    def __get_request(self, 
                      url_slug: str,
                      session: requests.Session, 
                      params: Optional[dict[str, str]] = None) -> Response:
        """Sends a GET request to the server"""
        while True:
            try:
                response = session.get(BASE_URL.format(url_slug),
                                       headers=HEADERS,
                                       proxies={"http": self.proxy,
                                                "https": self.proxy},
                                       verify=False,
                                       params=params)
                
                if response.ok:
                    return response
                
            except:self.logger.error("")
    
    def __post_request(self, 
                       url_slug: str,
                       session: requests.Session,
                       payload: dict[str, str],
                       params: Optional[dict[str, str]] = None) -> Response:
        """Sends a post request to the server"""
        while True:
            try:
                response = session.post(BASE_URL.format(url_slug),
                                        headers=HEADERS,
                                        proxies={"http": self.proxy,
                                                 "https": self.proxy},
                                        verify=False,
                                        params=params,
                                        data=urlencode(payload))
                
                if response.ok:
                    return response
                
            except: self.logger.error("")
    
    def __extract_properties(self, response: Response) -> None:
        """Extracts the properties from the login response"""
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.select_one("table#MainContent_PropertiesGV")

        for row in table.select("tr")[1:]:
            columns = row.select("td")

            property_id = re.search(r"Back\('(.+)',", columns[7].a["href"])

            cert_no = columns[2].get_text(strip=True)

            self.properties[cert_no] = property_id.group(1)

    def __extract_payload(self, response: Response) -> dict[str, str]:
        """"""
        soup = BeautifulSoup(response.text, "html.parser")

        payload = {}

        for field in soup.select("input"):
            try:
                name = field["name"]

                payload[name] = field["value"]
            except:pass
        
        return payload
    
    def __extract_updates(self, payload: dict[str, str]) -> dict[str, str]:
        """Extracts the updates to the payload"""
        return {"__VIEWSTATE": payload["__VIEWSTATE"],
                "__VIEWSTATEGENERATOR": payload["__VIEWSTATEGENERATOR"],
                "__PREVIOUSPAGE": payload["__PREVIOUSPAGE"],
                "__EVENTVALIDATION": payload["__EVENTVALIDATION"],
                "__SCROLLPOSITIONY": str(random.randrange(700, 920))}
    
    def run(self) -> None:
        """Entry point to the updater"""
        session, payload = self.__login()

        for item in self.cert_list[9:]:
            cert_no = item["Cert No"]

            try:
                event_target = self.properties[cert_no]

                payload.update({
                    "ctl00$ctl06": "ctl00$MainContent$ctl00|{}".format(event_target),
                    "__EVENTTARGET": event_target,
                    "__ASYNCPOST": "true"
                })

            except:
                self.logger.error(f"Property with cert no {cert_no} not found!")

                continue

            self.__post_request("/portal/BUYER/", session, payload)
            
            response = self.__get_request("/portal/BUYER/NTR", session)

            item_payload = self.__extract_payload(response)

            UPDATE_BTN.update(self.__extract_updates(item_payload))

            response = self.__post_request("/portal/BUYER/NTR", session, UPDATE_BTN)

            update_payload = self.__extract_payload(response)

            UPDATE.update(self.__extract_updates(update_payload))
            
            self.__post_request("/portal/BUYER/NTR", session, UPDATE)

            self.logger.info("Property with cert no {} updated.".format(cert_no))

            self.crawled.append("")

            self.logger.info("Queue: {} || Crawled: {}".format(
                len(self.cert_list) - len(self.crawled), len(self.crawled)))
            
            time.sleep(3)
        
        self.logger.info("Done.")


if __name__ == "__main__":
    app = AttorneyFeeUpdater()
    app.run()