# from Proxy_List_Scrapper import Scrapper, Proxy, ScrapperException

# scrapper = Scrapper("ALL", print_err_trace=False)

# data = scrapper.getProxies()

# print(data)

# for proxy in data:
#     print(proxy)

import requests
from bs4 import BeautifulSoup
# from fp.fp import FreeProxy

# while True:
#     try:
#         proxy = FreeProxy(country_id=["US"]).get()

#         # print(proxy)

#         proxies = {"http": proxy,
#                    "https": proxy}
        
#         print(proxies)

#         response = requests.get("https://land.wvsao.gov/", 
#                                 verify=False, 
#                                 proxies=proxies,
#                                 timeout=15)

#         print(response.status_code)

#         with open("sample1.html", "w", encoding="utf-8") as file:
#             file.write(str(response.text))
        
#         break
#     except Exception as e: print(e)

response = requests.get("https://sslproxies.org/")

soup = BeautifulSoup(response.text, "html.parser")

proxies = []

for row in soup.select("table tbody tr"):
    try:
        if row.select("td")[2].get_text(strip=True) != "US":
            continue

        proxies.append("http://{}:{}".format(
            row.select("td")[0].get_text(strip=True),
            row.select("td")[1].get_text(strip=True)
        ))
    except:pass

print(proxies)

import random

while True:
    try:
        proxy = random.choice(proxies)

        proxies_ = {"http": proxy,
            "https": proxy}

        print(proxies_)

        response = requests.get("https://land.wvsao.gov/", 
                                verify=False, 
                                proxies=proxies_,
                                timeout=15)

        print(response.status_code)

        soup = BeautifulSoup(response.text, "html.parser")

        print(soup.select("form")[0])

        with open("sample1.html", "w", encoding="utf-8") as file:
            file.write(str(response.text))
        
        break
    except Exception as e: print(e)