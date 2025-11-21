import os, sys

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the directory to sys.path
sys.path.insert(0, current_dir)

from Verify_Result_without_img import Result