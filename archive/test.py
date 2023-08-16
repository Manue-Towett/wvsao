import pandas
import json

df = pandas.read_csv("./input/certnopivot.csv")

cert_dict = df.to_dict("records")

with open("sample.json", "w") as file:
    json.dump(cert_dict, file, indent=4)