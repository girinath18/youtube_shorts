import boto3
import os
import re
import yt_dlp
import pandas as pd
import requests
import json
from datetime import datetime
import cv2
import logging

# Setup logging
logging.basicConfig(filename='video_downloader.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(message)s')

def clean_text(text):
    cleaned_text = re.sub(r'[^\w\s\.]', '', text)
    return cleaned_text

def is_video_playable(file_path):
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False
        ret, frame = cap.read()
        cap.release()
        return ret
    except Exception as e:
        logging.error(f"Error checking video playability: {e}")
        return False

def download_youtube_shorts(url, output_folder):
    retries = 3
    for attempt in range(retries):
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(output_folder, '%(id)s.%(ext)s')
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                video_id = info_dict.get("id", "")
                title = clean_text(info_dict.get('title', ''))
                description = clean_text(info_dict.get('description', ''))
                filename = f"{video_id}.mp4"
                filepath = os.path.join(output_folder, filename)

                metadata_file = os.path.join(output_folder, f"{video_id}_metadata.txt")
                with open(metadata_file, "w") as f:
                    f.write(f"Title: {title}\n")
                    f.write(f"Description: {description}\n")
                    f.write(f"Video ID: {video_id}\n")

                logging.info(f"Video downloaded successfully: {filename}")
                return title, description, video_id, filename, filepath
        except Exception as e:
            logging.error(f"Error downloading video from URL {url}: {e}")
            if attempt < retries - 1:
                logging.info(f"Retrying download... ({attempt + 1}/{retries})")
            else:
                logging.error(f"Failed to download video after {retries} attempts.")
                return None, None, None, None, None

def upload_video(file_name, file_path):
    try:
        with open(file_path, 'rb') as file:
            binary_data = file.read()

        url = 'https://storage.bunnycdn.com/kaptivate/prod/'
        access_key = '7b8d3799-ffff-4d96-8d41f4e535a1-f88f-4104'

        headers = {
            'AccessKey': access_key,
            'Content-Type': 'application/octet-stream'
        }

        response = requests.put(url + file_name, headers=headers, data=binary_data)

        if response.status_code == 201:
            logging.info(f"Video uploaded successfully: {file_name}")
            return True
        else:
            logging.error(f"Error uploading video {file_name}: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error uploading video {file_name}: {e}")
        return False

def create_post(title, description, category, subcategory, file_name):
    try:
        url = 'https://lwbauabdrh.execute-api.ap-south-1.amazonaws.com/prod/create-post/'

        headers = {
            'Content-Type': 'application/json',
        }

        payload = {
            "title": title,
            "description": description,
            "category": category,
            "subCategory1": subcategory,
            "source": file_name,
            "views": 0
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            logging.info(f"Post for video {file_name} created successfully!")
            return True
        else:
            logging.error(f"Error creating post for video {file_name}: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error creating post for video {file_name}: {e}")
        return False

def download_and_clear_bucket(bucket_name):
    grant = boto3.Session(region_name='us-east-1')
    s3client = grant.client('s3')
    s3resource = grant.resource('s3')
    bucket = s3resource.Bucket(bucket_name)

    base_dir = os.path.join(os.getcwd(), 'carnival')
    os.makedirs(base_dir, exist_ok=True)
    print(f"Data will be stored in: {base_dir}")

    try:
        for obj in bucket.objects.all():
            file_path = os.path.join(base_dir, obj.key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            bucket.download_file(obj.key, file_path)
            print(f"Downloaded {obj.key} to {file_path}")

        bucket.objects.delete()
        print(f"Emptied bucket: {bucket_name}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        return base_dir

def process_files_in_carnival(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".mp4"):
                file_path = os.path.join(root, file)
                category = os.path.basename(os.path.dirname(root))
                subcategory = os.path.basename(root)

                title = "Downloaded Video"
                description = "Description of downloaded video"

                if is_video_playable(file_path):
                    if upload_video(file, file_path) and create_post(title, description, category, subcategory, file):
                        logging.info(f"Processed and uploaded video: {file}")
                    else:
                        logging.error(f"Failed to upload or create post for video: {file}")
                else:
                    logging.error(f"Video {file} is not playable.")

def main():
    bucket_name = input("Enter the S3 bucket name: ")
    youtube_urls_file = input("Enter the path to the text file with YouTube URLs: ")
    output_folder = 'your_output_folder'
    
    # Read YouTube URLs from the text file
    try:
        with open(youtube_urls_file, 'r') as file:
            urls = file.readlines()
        
        # Process each URL
        for url in urls:
            url = url.strip()
            if url:
                download_youtube_shorts(url, output_folder)
    except Exception as e:
        logging.error(f"Error reading YouTube URLs file: {e}")

    base_dir = download_and_clear_bucket(bucket_name)
    print(f"All data downloaded to: {base_dir}")

    process_files_in_carnival(base_dir)

if __name__ == "__main__":
    main()
