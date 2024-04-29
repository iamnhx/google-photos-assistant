#!/bin/bash

# 1) Replace source with edited file.
directory="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Find files ending with -edited, searching 3 levels deep and handling spaces in directory names
find "$directory" -mindepth 1 -maxdepth 3 -type f -name '*-edited.*' -print0 | while IFS= read -r -d '' edited_file; do
    # Extract the base filename without the "-edited" part
    source_file=$(echo "$edited_file" | sed 's/-edited//')
    
    # Check if the source file exists
    if [ -f "$source_file" ]; then
        # Remove the source file
        rm "$source_file"
        
        # Rename the edited file to remove the "-edited" part
        mv "$edited_file" "$source_file"
        
        # Output actions to console
        echo "Deleted: $source_file"
        echo "Renamed: $edited_file -> $source_file"
    else
        # Output source file not found to console
        echo "Source file not found for $edited_file"
    fi
done

# 2) Process image and JSON pairs
for year in {2014..2023}; do poetry run python metadata.py -i "Google Photos/Photos from $year/" -o "/Google Photos/$year/"; done

# 3) Standardization into HEIC and MOV formats
cd "Google Photos"

for year in [0-9][0-9][0-9][0-9]; do
    if [ -d "$year" ]; then 
        cd "$year"
        
        # Process JPG files
        if ls *.jpg 1> /dev/null 2>&1; then
            for f in *.jpg; do
                heif-enc -q 100 "$f" -o "${f%.jpg}.heic"
                rm "$f"
            done
        fi

        # Process MP4 files
        if ls *.mp4 1> /dev/null 2>&1; then
            for file in *.mp4; do
                ffmpeg -i "$file" -c copy "${file%.*}.mov"
                rm "$file"
            done
        fi

        cd ..
    fi
done

