# Maintainer: https://github.com/changisaac

import pdb
from disjoint_set import DisjointSet
import pymongo
from libs import s3_download

from libs.guard_constants import GUARD_DB_HOST, GUARD_DB, GUARD_COL, COLLECTOR_COL, \
    S3_BUCKET_NAME, S3_IMAGES_LOCATION, IMG_FILE_TYPE, IMG_META_DATA_FILE_NAME

def connect_db():
    client = pymongo.MongoClient(GUARD_DB_HOST)
    db = client[GUARD_DB]

    return db, client

# basic tag based query which passes in mongodb query
def query_by_tags(query, group_adjacent=True):
    if len (query) == 0:
        return None

    res = []
    
    db, cl = connect_db()
    guard_col = db[GUARD_COL]
    iterator = guard_col.find(query)
    
    for doc in iterator:
        res.append(doc)

    # for the same collector_id and collection_seq
    # group adjacently connected rows
    if group_adjacent is True:
        frame_lookup = {}
       
        for i in range(len(res)):
            hash_key = hash(res[i]["collector_id"] + res[i]["collection_seq"] + res[i]["frame"])
            frame_lookup[hash_key] = i

        ds = DisjointSet()
        
        # for each unique frame, union it with its start and end frame
        for frame_key, idx in frame_lookup.items():
            # union with start frame even if start frame doesn't exist
            start_key = hash(res[idx]["collector_id"] + res[idx]["collection_seq"] + res[idx]["start_frame"])
            
            if start_key in frame_lookup and ds.find(frame_key) != ds.find(start_key):
                ds.union(frame_key, start_key)
            
            # union with end frame even if end fram doesn't exist
            end_key = hash(res[idx]["collector_id"] + res[idx]["collection_seq"] + res[idx]["end_frame"])
            
            if end_key in frame_lookup and ds.find(frame_key) != ds.find(end_key):
                ds.union(frame_key, end_key)

        grouped_res = []

        for group in list(ds.itersets()):
            scenario = []
            
            for hash_key in group:
                # will only group frames in detected set only
                if hash_key in frame_lookup:
                    scenario.append(res[frame_lookup[hash_key]])
        
            scenario = sorted(scenario, key = lambda i: i['frame']) 
            
            grouped_res.append(scenario)
        
        cl.close()
        return grouped_res

    return res

def get_location_query():
    pass

# takes in main db row queries and queries collector_fram_metadata collection
def download_query(query_res, grouped=True):
    # get location in s3
    db, cl = connect_db()
    collector_col = db[COLLECTOR_COL]

    all_s3_locations = []

    for scenario in query_res:
        scenario = sorted(scenario, key = lambda i: i['frame']) 
        
        # assumme adjanceency
        if len(scenario) == 1:
            # skip one frame detections for now
            continue
            
            frame_range = []
            
            iterator = collector_col.find(
                {
                    #TODO: database doesn't include colletor_id right now
                    #"collector_id": frame["collector_id"],
                    "collection_seq": scenario[0]["collection_seq"],
                    "frame": scenario[0]["frame"]
                }
            )

            for doc in iterator:
                all_s3_locations.append([doc["s3_location"]])

        elif len(scenario) > 1:
            scenario_s3_locations = []
            
            for i in range(len(scenario)-1):
                frame_range = []

                # given say 0000001000 to 0000001100 return all image frames in between
                start_bound = int(scenario[i]["frame"].lstrip("0"))
                end_bound =  int(scenario[i+1]["frame"].lstrip("0"))

                if i < len(scenario) - 2:
                    for j in range(start_bound, end_bound):
                        frame_range.append(str(j).zfill(10))
                else:
                    for j in range(start_bound, end_bound+1):
                        frame_range.append(str(j).zfill(10))

                for f in frame_range:
                    iterator = collector_col.find(
                        {
                            #TODO: database doesn't include colletor_id right now
                            #"collector_id": frame["collector_id"],
                            "collection_seq": scenario[i]["collection_seq"],
                            "frame": f
                        }
                    )

                    for doc in iterator:
                        scenario_s3_locations.append(doc["s3_location"])
            
            all_s3_locations.append(scenario_s3_locations)

    cl.close()

    for x in all_s3_locations:
        print(x)
        print("")

    # run s3 download
    #s3_download.download_process(all_s3_locations)

if __name__ == "__main__":
    ex_query_1 = {
        "car": {"$gt": 0}
        }
    
    ex_query_2 = {
        "traffic light": {"$gt": 0}
        }

    ex_query_3 = {
        "car": {"$gt": 0},
        "traffic light": {"$gt": 0}
        }

    res = query_by_tags(ex_query_3)

    if res is not None:
        for r in res:
            for x in r:
                print(x)

            print("")

    #download_query(res)
