#!/bin/bash

# Script to iterate through all subfolders in "workspace" and run "python all.py {subfolder_name}"
# Usage: ./iterate_subfolders.sh

# Set the parent folder to "workspace"
PARENT_FOLDER="workspace"

# Check if workspace folder exists
if [ ! -d "$PARENT_FOLDER" ]; then
    echo "Error: Directory 'workspace' does not exist."
    echo "Make sure you're running this script from the directory that contains the workspace folder."
    exit 1
fi

echo "Iterating through subfolders in workspace/"
echo "Running: venv/bin/python all.py {subfolder_name} in each subfolder"
echo "----------------------------------------"

# Counter for subfolders found
count=0

# Iterate through all items in the parent folder
for item in "$PARENT_FOLDER"/*; do
    # Check if item is a directory (subfolder)
    if [ -d "$item" ]; then
        subfolder_name=$(basename "$item")
        count=$((count + 1))
        
        echo "[$count] Processing: $subfolder_name"
        echo "Full path: $item"
        echo "Running: venv/bin/python all.py $subfolder_name"
        
        # Execute venv/bin/python all.py with the subfolder name as argument
        ./venv/bin/python all.py "$subfolder_name"
        
        # Return to the original directory
        cd - > /dev/null
        
        echo "----------------------------------------"
    fi
done

if [ $count -eq 0 ]; then
    echo "No subfolders found in workspace/"
else
    echo "Processed $count subfolder(s)."
fi
