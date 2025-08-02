import os
import json
import argparse
from typing import Dict, Any

from src.tts.base import TTSEngine
from src.tts.engine_factory import TTSEngineFactory
from src.vclip_processor import process_vclip

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert virtual clips JSON to clips with audio TTS files"
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
        default='vclips.json',
        help="Input scenes JSON filename (default: vclips.json)"
    )

    # Optional output file argument
    parser.add_argument(
        '--output',
        type=str,
        default='ttsclips.json',
        help="Output virtual clips JSON filename (default: ttsclips.json)"
    )

    # Optional audio output directory argument
    parser.add_argument(
        '--audio_output',
        type=str,
        default='tts_audio_lib',
        help="Output directory for generated audio files (default: tts_audio_lib)"
    )

    return parser.parse_args()

def ensure_workspace_directory(project_name: str) -> str:
    """
    Ensure the workspace directory for the project exists.

    Args:
        project_name (str): Name of the project

    Returns:
        str: Path to the project workspace directory

    Raises:
        ValueError: If the workspace directory does not exist or is not a directory
    """
    workspace_dir = os.path.join('workspace', project_name)

    # Check if the directory exists
    if not os.path.exists(workspace_dir):
        raise ValueError(f"Workspace directory does not exist: {workspace_dir}")

    # Check if it's actually a directory
    if not os.path.isdir(workspace_dir):
        raise ValueError(f"Workspace path is not a directory: {workspace_dir}")

    return workspace_dir

def convert_tts_project(
    input_json: Dict[str, Any],
    project_name: str,
    audio_output: str
) -> Dict[str, Any]:
    """
    Convert the input project JSON by processing TTS.

    Args:
        input_json (Dict[str, Any]): Input project configuration
        project_name (str): Name of the project
        audio_output (str): Output directory for audio files

    Returns:
        Dict[str, Any]: Processed project configuration with TTS
    """
    # Create output directory for audio files globally under current directory
    output_dir = os.path.join(audio_output)
    os.makedirs(output_dir, exist_ok=True)

    # Process each video clip with its specific TTS engine
    processed_clips = []
    for clip_index, clip in enumerate(input_json.get('vclips', [])):
        try:
            # Process the clip
            processed_clip = process_vclip(clip, output_dir)
            processed_clips.append(processed_clip)

        except ValueError as e:
            raise ValueError(f"Error processing clip {clip_index}: {e}")

    # Create a copy of the input JSON with processed clips
    processed_json = input_json.copy()
    processed_json['vclips'] = processed_clips

    return processed_json

def main():
    """
    Main entry point for scene to virtual clips conversion.
    Supports CLI with project name, input, and output file specification.
    """
    # Parse command-line arguments
    args = parse_arguments()

    try:
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
            output_json = convert_tts_project(
                input_json,
                project_name=args.project,
                audio_output=args.audio_output
            )
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
            print("Conversion successful:")
            print(f"Input:  {input_path}")
            print(f"Output: {output_path}")
            print(f"Audio:  {os.path.abspath(args.audio_output)}")
        except Exception as e:
            print(f"Error writing output file: {e}")

    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()