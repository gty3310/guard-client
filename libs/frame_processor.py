# Maintainer: https://github.com/changisaac

import pdb
import glob
import cv2
from object_detection.generic_detector import GenericDetector
import os
import json
import subprocess
import pymongo
import boto3

# import constants
from guard_constants import GUARD_DB_HOST, GUARD_DB, GUARD_COL, COLLECTOR_COL, \
    S3_BUCKET_NAME, S3_IMAGES_LOCATION, IMG_FILE_TYPE, IMG_META_DATA_FILE_NAME

def process_images(
    img_dir,
    img_type,
    out_dir=None,
    out_json=None,
    drop_rate=6):
    
    # generic yolov3 classifier trained off coco dataset
    det = GenericDetector()

    """
    Note on detection drop rate (dr):

    ex: collection at 6fps and detection at 1dr = detection at 6fps in reality
    ex: collection at 6fps and detection at 2dr = detection at 3fps in reality
    ex: collection at 6fps and detection at 6dr = detection at 1fps in reality
    ex: collection at 6fps and detection at 12dr = detection at 0.5fps in reality
    
    In terms of time saved for inferencing, dropping frames will divide the total time to
    inference the entire dataset by the drop rate. Ex: 2dr will result in half the time
    to inference.
    """

    # list of image files to run detection on
    img_files = glob.glob(img_dir + "/*." + img_type)
    
    # assumed that images are named chronogically
    # this is so dropped frames happen chronologically
    img_files.sort()

    # removing dropped frames from image files based on detector drop rate
    # drop rate of 3 is only run detection on every third frame
    img_files_dropped = img_files[::drop_rate]

    agg_detections = []

    for i in range(len(img_files_dropped)):
        frame = cv2.imread(img_files_dropped[i])
        detections = None
     
        # run yolov3 model detection on opencv frame
        if out_dir is not None:
            # only write images with bounding boxes drawn on if out_dir specified
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
        
            img_name = img_files_dropped[i].split("/")[-1]
            detections = det.process_frame(frame, out_dir + "/" + img_name)
        else:
            detections = det.process_frame(frame)

        # aggregate detections for output
        agg_detections.append((img_name, detections))

    # only write to json file if out_json specified otherwise return detections
    if out_json is not None:
        with open(out_json, 'w') as f:
            json.dump(agg_detections, f)
    else:
        return agg_detections

def process_bags(img_bag_file, img_out_dir, img_topic, gps_json, collector_id):
    # set up client for mongodb
    client = pymongo.MongoClient(GUARD_DB_HOST)
    db = client[GUARD_DB]

    # 2 collections: 1 for detections and 1 for frame by frame meta data
    guard_col = db[GUARD_COL]
    collector_col = db[COLLECTOR_COL]

    # load images in rosbag file to file system using external python2 script
    # load image meta data to json in img_out_dir
    # assume script for writing ros bags to png files is in same directory
    """
    load_imgs_cmd = "./rosimg_to_img.py -b " + img_bag_file +" -d " + img_out_dir + " -t " + img_topic
    
    process = subprocess.run(load_imgs_cmd.split())
    process.check_returncode()
    """

    # run object detection on images and output detections to json
    object_detections_dir = img_out_dir + "/object_detections"
    object_detections_json = img_out_dir+"/object_detections.json"
    
    """
    process_images(
        img_dir=img_out_dir,
        img_type=IMG_FILE_TYPE,
        out_json=object_detections_json,
        out_dir=object_detections_dir,
        drop_rate=100) 
    """

    # load in gps lookup table, key is unix timstamp (seconds)
    gps_lookup = None
    with open(gps_json) as f:
        gps_lookup = json.load(f)
   
    # load in object detections
    detections = None
    with open(object_detections_json) as f:
        detections = json.load(f)
    
    # load in image meta data
    image_data = None
    with open(img_out_dir + "/" + IMG_META_DATA_FILE_NAME) as f:
        image_data = json.load(f)    

    # upload all images written out to img_out_dir to s3
    s3 = boto3.resource('s3')
    # use collector_id and timestamp of first image for s3 reference
    s3_img_location = \
        S3_IMAGES_LOCATION + "/" + collector_id + "/" + str(image_data["0000000000.png"]["timestamp_nsec"])

    img_files = glob.glob(img_out_dir + "/*." + IMG_FILE_TYPE)
    
    for i in range(len(img_files)):
        img_name_s3 = s3_img_location + "/" + img_files[i].split("/")[-1]
        # update image meta_data wuth s3 locations
        image_data[img_files[i].split("/")[-1]]["s3_location"] = img_name_s3
        print(img_name_s3)
        #s3.Bucket(S3_BUCKET_NAME).upload_file(img_files[i], img_name_s3)    

    collection_seq = str(image_data["0000000000.png"]["timestamp_nsec"])
    
    # write out all frame meta data to collector frame meta_data in db
    for img, data in image_data.items():
        img_doc = {}

        img_doc["collection_seq"] = collection_seq
        img_doc["frame"] = img.split(".")[0]

        for key, val in data.items():
            img_doc[key] = val

        res = collector_col.insert_one(img_doc)
        print(res)
    
    # json dump new image data back into image meta_data.json
    with open(img_out_dir + "/" + IMG_META_DATA_FILE_NAME, "w") as f:
        json.dump(image_data, f)

    # write out all detection data to main collection in db
    for i in range(len(detections)):
        det_doc = {}
        
        image_name = detections[i][0]
        timestamp_ns =  image_data[image_name]["timestamp_nsec"]
        timestamp_s = int(int(timestamp_ns) * 10 ** -9)

        det_doc["collection_seq"] = collection_seq 
        det_doc["collector_id"] = collector_id
        det_doc["timestamp_nsec"] = timestamp_ns  
        det_doc["latitude"] = gps_lookup[str(timestamp_s)]["latitude"]
        det_doc["longitude"] = gps_lookup[str(timestamp_s)]["longitude"]
        det_doc["speed_m_s"] =  gps_lookup[str(timestamp_s)]["speed_m_s"]

        curr_frame = None
        next_frame = None
        prev_frame = None

        curr_frame = detections[i][0].split(".")[0]
        det_doc["frame"] = curr_frame
        
        if i == 0:
            next_frame = detections[i+1][0].split(".")[0]
            det_doc["start_frame"] = curr_frame
            det_doc["end_frame"] = next_frame 
        elif i == (len(detections) - 1):
            prev_frame = detections[i-1][0].split(".")[0]
            det_doc["start_frame"] = prev_frame
            det_doc["end_frame"] = curr_frame
        else:
            prev_frame = detections[i-1][0].split(".")[0]
            next_frame = detections[i+1][0].split(".")[0]
            det_doc["start_frame"] = prev_frame
            det_doc["end_frame"] = next_frame

        for objects in detections[i][1]:
            if objects[1] not in det_doc:
                det_doc[objects[1]] = 1
            else:
                det_doc[objects[1]] += 1

        x = guard_col.insert_one(det_doc)
        print(x.inserted_id)

def main():
    process_bags(
        img_bag_file="/home/shared/av_data/bags/daylight_exposure_3000.bag",
        img_out_dir="/home/shared/av_data/test", 
        img_topic="/camera/infra1/image_rect_raw",
        gps_json="/home/shared/av_data/gps/20200306-175204.json",
        collector_id="testuser")

if __name__ == "__main__":
    main()

