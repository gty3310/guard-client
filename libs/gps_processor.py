# Maintainer: https://github.com/changisaac

import pdb
import time
import datetime
import gpx_parser as parser
import json
from datetime import timezone

def gpx_to_json(gpx_file, json_file):
    lookup = {}

    with open(gpx_file, 'r') as f:
        gpx = parser.parse(f)
        points = gpx[0].points

        for i in range(len(points)):
            key = int(points[i].time.replace(tzinfo=timezone.utc).timestamp())
            lookup[key] = {}
            lookup[key]["latitude"] = points[i].latitude
            lookup[key]["longitude"] = points[i].longitude

            if i < len(points)-1:
                lookup[key]["speed_m_s"] = points[i].speed_between(points[i+1])
            else:
                lookup[key]["speed_m_s"] = points[i-1].speed_between(points[i])

    with open(json_file, "w") as j:
        json.dump(lookup, j)

def main():
    gpx_to_json("/home/shared/av_data/gps/20200306-175204.gpx", "/home/shared/av_data/gps/20200306-175204.json")

if __name__ == "__main__":
    main()
