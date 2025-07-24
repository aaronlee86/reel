import os
import json
import argparse
from src.converter import convert_video_project

def parse_arguments():
    """
    Parse command-line arguments

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert scene JSON to virtual clips JSON"
    )

    # Positional argument for project name
    parser.add_argument(
        'project',
        type=str,
        help="Project name (used for creating workspace directory)"
    )

    # Optional input file argument
    parser.add_argument(
        '--input',
        type=str,
        default='scenes.json',
        help="Input scenes JSON filename (default: scenes.json)"
    )

    # Optional output file argument
    parser.add_argument(
        '--output',
        type=str,
        default='vclips.json',
        help="Output virtual clips JSON filename (default: vclips.json)"
    )

    return parser.parse_args()

def ensure_workspace_directory(project_name):
    """
    Ensure the workspace directory for the project exists

    Args:
        project_name (str): Name of the project

    Returns:
        str: Path to the project workspace directory

    Raises:
        ValueError: If the workspace directory does not exist
    """
    workspace_dir = os.path.join('workspace', project_name)

    # Check if the directory exists
    if not os.path.exists(workspace_dir):
        raise ValueError(f"Workspace directory does not exist: {workspace_dir}")

    # Check if it's actually a directory
    if not os.path.isdir(workspace_dir):
        raise ValueError(f"Workspace path is not a directory: {workspace_dir}")

    return workspace_dir

def main():
    """
    Main entry point for scene to virtual clips conversion
    Supports CLI with project name, input, and output file specification
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Create workspace directory
    workspace_dir = ensure_workspace_directory(args.project)

    # Construct full input and output paths
    input_path = os.path.join(workspace_dir, args.input)
    output_path = os.path.join(workspace_dir, args.output)

    # Read input JSON
    try:
        with open(input_path, 'r') as f:
            input_json = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file {input_path} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {input_path}")
        return

    # Convert the project
    try:
        output_json = convert_video_project(input_json, project_name=args.project)
    except ValueError as e:
        # Detailed error handling for conversion failures
        print(f"Conversion Error: {e}")
        return
    except Exception as e:
        print(f"Unexpected error during conversion: {e}")
        return

    # Write output JSON
    try:
        with open(output_path, 'w') as f:
            json.dump(output_json, f, indent=2)

        print(f"Conversion successful:")
        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    main()