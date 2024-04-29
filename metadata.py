import os
import re
import random
import argparse
import subprocess
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='execution.log')

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input-dir', type=str, help='Directory to read from', required=True)
parser.add_argument('-o', '--output-dir', type=str, help='Directory to write to', required=True)
args = parser.parse_args()

input_dir = args.input_dir
output_dir = args.output_dir
image_json_mapping = {}
multiple_pattern = r'\(\d+?\)'
image_set = set()
json_set = set()

# Function to generate unique filenames with letter suffixes
def generate_unique_filename(output_dir, base_filename, extension):
    candidate = os.path.join(output_dir, f"{base_filename}{extension}".lower())
    counter = 1  # Start numbering from 01
    while os.path.exists(candidate):
        candidate = os.path.join(output_dir, f"{base_filename}{counter:02}{extension}".lower())
        counter += 1
        if counter > 999:  # Allow up to 99 additional files
            raise ValueError("Too many files with the same base filename")
    return candidate

# Collect image and JSON files
for root, dirs, files in os.walk(input_dir):
    image_list = [f for f in files if not f.endswith('.json') and f != '.DS_Store']
    for image in image_list:
        image_set.add(os.path.join(root, image))
    json_list = [f for f in files if os.path.splitext(f)[1] == '.json' and f != 'metadata.json']
    for json_file in json_list:
        json_set.add(os.path.join(root, json_file))
        with open(os.path.join(root, json_file), 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        title = json_data['title'].replace("'", '_').replace(';', '_')
        title_base, title_ext = os.path.splitext(title)
        image_in_title = title_base[:51 - len(title_ext)] + title_ext
        json_base, json_ext = os.path.splitext(json_file)
        multiple_search = re.search(multiple_pattern, json_base)
        
        if multiple_search:
            multiple_text = multiple_search.group()
            image_in_title_base, image_in_title_ext = os.path.splitext(image_in_title)
            new_image_in_title = f"{image_in_title_base}{multiple_text}{image_in_title_ext}"
            if os.path.exists(os.path.join(root, new_image_in_title)):
                image_json_mapping[os.path.join(root, new_image_in_title)] = os.path.join(root, json_file)
            elif os.path.exists(os.path.join(root, image_in_title)):
                image_json_mapping[os.path.join(root, image_in_title)] = os.path.join(root, json_file)
            else:
                print(f'No image for json: {os.path.join(root, json_file)}')
        elif os.path.exists(os.path.join(root, image_in_title)):
            image_json_mapping[os.path.join(root, image_in_title)] = os.path.join(root, json_file)
        else:
            print(f'No image for json: {os.path.join(root, json_file)}')
            print(f'Image in title: {image_in_title}')

image_matches, json_matches = image_json_mapping.keys(), image_json_mapping.values()

# Process unmatched images
for image_path in image_set:
    if image_path not in image_matches:
        print(f'No json for image: {image_path}')
        image_filename = os.path.basename(image_path)
        image_base, image_ext = os.path.splitext(image_filename)
        new_image_filename = image_filename
        while os.path.exists(os.path.join(output_dir, new_image_filename)):
            new_image_filename = f"{image_base}{chr(97)}{image_ext}"  # Start with 'a' for a new timestamp
        new_image_path = os.path.join(output_dir, new_image_filename)
        copy_command = f'cp -v "{image_path}" "{new_image_path}"'
        logging.info(f'Running `{copy_command}`')
        process = subprocess.run(copy_command, shell=True, capture_output=True)
        stdout, stderr = process.stdout.decode('utf-8').strip(), process.stderr.decode('utf-8').strip()
        if stdout:
            logging.info(stdout)
        if stderr:
            logging.error(stderr)

# Check for unmatched JSON files
for json_file in json_set:
    if json_file not in json_matches:
        print(f'No image for json: {json_file}')

# Create output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.mkdir(output_dir)

# Process image and JSON pairs
for image_path, json_path in image_json_mapping.items():
    if not os.path.exists(image_path):
        print(f'Image does not exist: {image_path}')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    if 'photoTakenTime' not in json_data:
        print(f'No photoTakenTime: {json_path}')
    
    timestamp = int(json_data['photoTakenTime']['timestamp'])
    time = datetime.fromtimestamp(timestamp)
    time_str = time.strftime('%Y:%m:%d %H:%M:%S')
    
    md_list = [f'-DateTimeOriginal="{time_str}" -CreateDate="{time_str}"']
    
    if 'geoData' not in json_data:
        print(f'No geoData: {json_path}')
    
    latitude = json_data['geoData'].get('latitude')
    if latitude:
        md_list.append(f'-GPSLatitude={latitude} -GPSLatitudeRef=N')
    
    longitude = json_data['geoData'].get('longitude')
    if longitude:
        md_list.append(f'-GPSLongitude={longitude} -GPSLongitudeRef=E')
    
    altitude = json_data['geoData'].get('altitude')
    if altitude:
        md_list.append(f'-GPSAltitude={altitude} -GPSAltitudeRef="Above Sea Level"')
    
    if 'description' not in json_data:
        print(f'No description: {json_path}')
    
    description = json_data['description'].strip().replace('\n', ' ; ').replace('"', "'")
    if description:
        md_list.append(f'-Caption-Abstract="{description}" -Description="{description}" -ImageDescription="{description}"')
    
    # Generate a new image filename using numbers from 01 to 999 as suffixes
    new_image_base = time.strftime('%Y%m%d_%H%M%S')
    new_image_path = generate_unique_filename(output_dir, new_image_base, os.path.splitext(image_path)[1])
    
    outfile_str = f'-o "{new_image_path}"'
    md_list.append(outfile_str)
    
    logging.info(f'Original image: {image_path}')
    k_lower = image_path.lower()
    
    if k_lower.endswith(('.bmp', '.avi', '.wmv', '.mkv')):
        copy_command = f'cp -v "{image_path}" "{new_image_path}"'
    else:
        exiftool_command = f'exiftool "{image_path}" {" ".join(md_list)} -m'
    
    logging.info(f'Running `{copy_command if k_lower.endswith(('.bmp', '.avi', '.wmv', '.mkv')) else exiftool_command}`')
    
    process = subprocess.run(copy_command if k_lower.endswith(('.bmp', '.avi', '.wmv', '.mkv')) else exiftool_command,
                             shell=True, capture_output=True)
    
    stdout, stderr = process.stdout.decode('utf-8').strip(), process.stderr.decode('utf-8').strip()
    if stdout:
        logging.info(stdout)
    if stderr:
        logging.error(stderr)
        
        if 'looks more like a JPEG' in stderr:
            k_jpeg = os.path.splitext(image_path)[0] + '.jpg'
            new_image_base = time.strftime('%Y%m%d_%H%M%S')
            new_image_path_jpeg = generate_unique_filename(output_dir, new_image_base, '.jpg')
            copy_command = f'cp -v "{image_path}" "{k_jpeg}"'
            
            logging.info(f'Running `{copy_command}`')
            
            process = subprocess.run(copy_command, shell=True, capture_output=True)
            stdout, stderr = process.stdout.decode('utf-8').strip(), process.stderr.decode('utf-8').strip()
            
            if stdout:
                logging.info(stdout)
            if stderr:
                logging.error(stderr)
            
            md_list[-1] = f'-o "{new_image_path_jpeg}"'
            exiftool_command = f'exiftool "{k_jpeg}" {" ".join(md_list)} -m'
            
            logging.info(f'Running `{exiftool_command}`')
            
            process = subprocess.run(exiftool_command, shell=True, capture_output=True)
            stdout, stderr = process.stdout.decode('utf-8').strip(), process.stderr.decode('utf-8').strip()
            
            if stdout:
                logging.info(stdout)
            if stderr:
                logging.error(stderr)
    
    logging.info(f'New image: {new_image_path}')
