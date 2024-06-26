import os
import re
from pytube import YouTube
import pandas as pd
import requests
import json
from datetime import datetime
import cv2

def clean_text(text):
    # Remove special characters and emojis using re
    cleaned_text = re.sub(r'[^\w\s\.]', '', text)
    return cleaned_text

def is_video_playable(file_path):
    """
    Check if the video file is playable using OpenCV.
    """
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False
        ret, frame = cap.read()
        cap.release()
        return ret
    except Exception as e:
        print(f"Error checking video playability: {e}")
        return False

def download_youtube_shorts(url, output_folder):
    try:
        yt = YouTube(url)
        streams = yt.streams
        streams.filter(progressive=True)
        stream = streams.get_highest_resolution()
        if stream:
            # Download the video
            video_file = stream.download(output_folder)

            # Extract metadata
            title = clean_text(yt.title)
            description = clean_text(yt.description)
            video_id = yt.video_id

            # Generate file name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"{video_id}_{timestamp}.mp4"
            new_filepath = os.path.join(output_folder, new_filename)
            os.rename(video_file, new_filepath)

            # Save metadata to a text file
            metadata_file = os.path.join(output_folder, f"{video_id}_metadata.txt")
            with open(metadata_file, "w") as f:
                f.write(f"Title: {title}\n")
                f.write(f"Description: {description}\n")
                f.write(f"Video ID: {video_id}\n")

            print("Video downloaded successfully!")

            return title, description, video_id, new_filename, new_filepath
        else:
            print("No suitable streams found for the video.")
            return None, None, None, None, None
    except Exception as e:
        print(f"Error downloading video from URL {url}: {e}")
        return None, None, None, None, None

def upload_video(file_name, file_path):
    try:
        # Read the binary data from the video file
        with open(file_path, 'rb') as file:
            binary_data = file.read()

        url = 'https://storage.bunnycdn.com/kaptivate/prod/'
        access_key = '7b8d3799-ffff-4d96-8d41f4e535a1-f88f-4104'

        # Headers with your access key
        headers = {
            'AccessKey': access_key,
            'Content-Type': 'application/octet-stream'  # Specify content type as binary
        }

        # Make a PUT request to the API endpoint with binary data in the request body
        response = requests.put(url + file_name, headers=headers, data=binary_data)

        # Check if the request was successful (status code 201)
        if response.status_code == 201:
            print(f"Video {file_name} uploaded successfully!")
            return True
        else:
            # If the request was not successful, print the error status code
            print(f"Error uploading video {file_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error uploading video {file_name}: {e}")
        return False

def create_post(title, description, category, subcategory, file_name):
    try:
        url = 'https://lwbauabdrh.execute-api.ap-south-1.amazonaws.com/prod/create-post/'

        # Define headers with your access key
        headers = {
            'Content-Type': 'application/json',  # Specify content type as JSON
        }

        # Fetch views count from the YouTube video
        yt = YouTube(f"https://www.youtube.com/watch?v={file_name[:-4]}")
        views_count = yt.views

        # Define the JSON payload
        payload = {
            "title": title,
            "description": description,
            "category": category,
            "subCategory1": subcategory,
            "source": file_name,  # Using file_name directly
            "views": views_count  # Include views count in the payload
        }

        # Make a POST request to the API endpoint with binary data in the request body
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            print(f"Video {file_name} uploaded successfully!")
            return True
        else:
            # If the request was not successful, print the error status code
            print(f"Error uploading video {file_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error uploading video {file_name}: {e}")
        return False

def main():
    input_file = input("Enter the path to the input text file: ")

    # Read input file into a list of lines
    with open(input_file, 'r') as f:
        lines = f.readlines()

    extracted_data = []
    success_count = 0
    failure_count = 0

    for line in lines:
        # Split each line by comma to get URL, Category, Subcategory
        parts = line.strip().split(',')
        # Take the first three fields, even if there are more
        if len(parts) < 3:
            print(f"Skipping line due to incorrect format: {line}")
            failure_count += 1
            continue
        url, category, subcategory = parts[:3]

        output_folder = os.path.join(os.getcwd(), category, subcategory)

        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        print(f"Downloading video from URL: {url}")

        title, description, video_id, file_name, file_path = download_youtube_shorts(url, output_folder)

        # Check if the download was successful
        if title and description and video_id and file_name and file_path:
            # Check if the video is playable
            if is_video_playable(file_path):
                # Call the function to upload the video
                if upload_video(file_name, file_path) and create_post(title, description, category, subcategory, file_name):
                    success_count += 1
                else:
                    failure_count += 1
            else:
                print(f"Video {file_name} is not playable and will not be uploaded.")
                failure_count += 1

            extracted_data.append({
                'URL': url,
                'Category': category,
                'Subcategory': subcategory,
                'Title': title,
                'Description': description,
                'Video ID': video_id
            })
        else:
            print(f"Failed to download video from URL: {url}")
            failure_count += 1

    # Convert the extracted data to a DataFrame
    extracted_df = pd.DataFrame(extracted_data)

    report_df = pd.DataFrame({
        'Success Count': [success_count],
        'Failure Count': [failure_count]
    })

    report_df.to_csv('upload_report.csv', index=False)
    print("Upload report saved successfully.")

if __name__ == "__main__":
    main()
