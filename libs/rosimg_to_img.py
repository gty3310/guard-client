#!/usr/bin/env python2

# Maintainer: https://github.com/changisaac

# uses python2 of the system where rosbag and cv_bridge is installed
# specifically used for sensor_msgs/Image message types

import rosbag
import cv2
from cv_bridge import CvBridge
import sys
import getopt
import json
import os

def main(argv):    
    img_bag = None
    img_dir = None
    img_topic = None

    try:
        opts, args = getopt.getopt(argv,"hb:d:t:",["bag=", "dir=", "topic="])
    except getopt.GetoptError:
        print('rosimg_to_img.py -b <bag_file> -d <image_directory> -t <topic>')
        sys.exit(2)

    if len(opts) == 0:
        print('rosimg_to_img.py -b <bag_file> -d <image_directory> -t <topic>')

    for opt, arg in opts:
        if opt == '-h':
            print('rosimg_to_img.py -b <bag_file> -d <image_directory> -t <topic>')
            sys.exit()
        elif opt in ("-b", "--bag_file"):
            img_bag = arg
        elif opt in ("-d", "--image_directory"):
            img_dir = arg
        elif opt in ("-t", "--topic"):
            img_topic = arg

    if img_bag is None or img_dir is None or img_topic is None:
        return 

    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    bag = rosbag.Bag(img_bag) 
    bridge = CvBridge()
    img_meta_data = {}

    i = 0

    for topic, msg, t in bag.read_messages(topics=[img_topic]):
        img_field = {}
        img_field["timestamp_nsec"] = t.to_nsec()
        img_field["height"] = msg.height
        img_field["width"] = msg.width
        img_field["encoding"] = msg.encoding

        img = bridge.imgmsg_to_cv2(msg, "mono8")
        img = cv2.equalizeHist(img)

        img_file = str(i).zfill(10) + ".png"
        
        img_meta_data[img_file] = img_field
        
        cv2.imwrite(img_dir + "/" + img_file, img)

        i += 1
    
    with open(str(img_dir) + "/meta_data.json", "w") as f:
        json.dump(img_meta_data, f)

if __name__ == "__main__":
    main(sys.argv[1:])

