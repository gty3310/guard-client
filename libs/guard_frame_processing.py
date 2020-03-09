# Maintainer: https://github.com/changisaac

import pdb
import glob
import cv2
from object_detection.generic_detector import GenericDetector
import os
import json

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
        agg_detections.append(detections)

    # only write to json file if out_json specified otherwise return detections
    if out_json is not None:
        with open(out_json, 'w') as f:
            json.dump(agg_detections, f)
    else:
        return agg_detections

def main():
    process_images(
        img_dir="/home/shared/av_data/daylight_exposure_3000_png",
        img_type="png",
        out_json="/home/shared/guard_client/libs/daylight_exposure_3000_png_detections.json",
        out_dir="/home/shared/av_data/daylight_exposure_3000_detected",
        drop_rate=100) 

if __name__ == "__main__":
    main()

