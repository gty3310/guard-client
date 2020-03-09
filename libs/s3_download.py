# Maintainer: https://github.com/7amim

from time import gmtime, strftime
import os
import boto3
import botocore
import shutil

forestai = 'forestai-guard'
download_directory = "/home/shared/av_data/download/"
# We want this to be relative path for deletion process
download_master_directory = 'master/'

def download(s3, aws_filename, downloadname, scenario_num):
    try:
        file = os.path.basename(os.path.normpath(aws_filename))
        downloadpath = aws_filename.split(file)[0]
        # TODO: Change 'test' to the first subdirectory in bucket
        # downloadpath = downloadname.split('test/')[1]
        scenario_dir = 'scenario' + str(scenario_num)
        full_download_path = download_directory + download_master_directory + scenario_dir  + '/' + downloadpath
        if not os.path.exists(full_download_path):
            os.makedirs(full_download_path)
        
        print("Downloading file from %s" % aws_filename)
        print("Downloading file to %s" % full_download_path)
        s3.Bucket(forestai).download_file(aws_filename, full_download_path + '/' + file)
        return full_download_path
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

def download_data(s3, list_of_s3_locations, user=None, ts=None):
    scenario_num = 0
    for scenario in list_of_s3_locations:
        for aws_filename in scenario:
            full_download_path = download(s3, aws_filename, download_directory, scenario_num)
        scenario_num += 1

    # After iterating through all the scenarios, zip the master folder with all scenarios
    zip_downloaded_data()
    # After zipping the folder, delete the path
    shutil.rmtree(download_directory + download_master_directory)

def zip_downloaded_data(user=None, ts=None):
    if user is None:
        user = 'default-user'
    if ts is None:
        ts = strftime("%Y-%m-%d_%H_%M_%S", gmtime())
    file = 'data_%s_%s' % (user, ts)
    shutil.make_archive(file, 'zip', download_master_directory)
    
def download_process(list_of_s3_locations):
    s3 = boto3.resource('s3')
    os.chdir(download_directory)
    download_data(s3, list_of_s3_locations)

def main():
    # list_of_s3_locations = [['test/user1/1583536661790281234/0.jpg', 'test/user1/1583536661790281234/1.jpg']]
    list_of_s3_locations = [['images/testuser/1583536382117/0000000001.png', 'images/testuser/1583536382117/0000000002.png'],
                            ['images/testuser/1583536382117/0000000003.png', 'images/testuser/1583536382117/0000000004.png'],
                            ['images/testuser/1583536382117/0000000010.png', 'images/testuser/1583536382117/0000000011.png']]
    download_process(list_of_s3_locations)

if __name__ == '__main__':
    main()
