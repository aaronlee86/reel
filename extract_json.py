import argparse
import json
import sys
import os
import pathlib

def extract_nested_key_values(data, key_path):
    """
    Recursively extract values for a key path from JSON data.

    Args:
        data (dict/list): JSON data to search
        key_path (str): Dot-separated key path to extract values for

    Returns:
        list: Extracted values
    """
    results = []

    def traverse(obj, keys):
        # Handle different data types
        if isinstance(obj, dict):
            # Check for key match at current level
            if keys[0] in obj:
                # If this is the last key in path
                if len(keys) == 1:
                    # If value is not a container, add to results
                    if not isinstance(obj[keys[0]], (dict, list)):
                        results.append(str(obj[keys[0]]))
                # Continue traversing if more keys in path
                else:
                    traverse(obj[keys[0]], keys[1:])

            # Continue searching through all values
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    traverse(value, keys)

        # Handle lists
        elif isinstance(obj, list):
            # Traverse each item in the list
            for item in obj:
                traverse(item, keys)

    # Split key path
    key_components = key_path.split('.')
    traverse(data, key_components)

    return results

def main():
    # Set up workspace path relative to current directory
    workspace_path = os.path.join(os.getcwd(), 'workspace')

    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description='Extract values for a specific key from a JSON file within a project folder.'
    )
    parser.add_argument('project_folder',
                        help='Project folder name within ./workspace')
    parser.add_argument('--input',
                        required=False,
                        default='vclips.json',
                        help='Relative path to input JSON file within the project folder')
    parser.add_argument('--key',
                        required=False,
                        default='tts.text',
                        help='Key name to extract. Supports nested keys at any level.')
    parser.add_argument('--output',
                        required=False,
                        default='subtitles.txt',
                        help='Relative path to output text file within the project folder')

    args = parser.parse_args()

    try:
        # Construct full project path within workspace
        project_folder = os.path.join(workspace_path, args.project_folder)
        project_folder = pathlib.Path(project_folder).resolve()

        # Construct full paths
        input_path = project_folder / args.input
        output_path = project_folder / args.output

        # Ensure workspace and project folder exist
        if not os.path.isdir(workspace_path):
            print(f"Error: Workspace folder '{workspace_path}' does not exist.", file=sys.stderr)
            sys.exit(1)

        # Ensure project folder exists
        if not project_folder.is_dir():
            print(f"Error: Project folder '{project_folder}' does not exist.", file=sys.stderr)
            sys.exit(1)

        # Read JSON file
        with open(input_path, 'r') as json_file:
            json_data = json.load(json_file)

        # Extract key values
        extracted_values = extract_nested_key_values(json_data, args.key)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to output file
        with open(output_path, 'w') as output_file:
            for value in extracted_values:
                output_file.write(f"{value}\n")

        print(f"Extracted {len(extracted_values)} values for key '{args.key}'")

    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied when accessing files.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{input_path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()