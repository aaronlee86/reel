import os
import json
import argparse
import sys
import hashlib
from typing import Dict, Any

from src.tts.base import TTSEngine
from src.tts.engine_factory import TTSEngineFactory
from src.vclip_processor import process_vclip, dryrun_filename

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

    # Optional dry-run flag
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Print text and audio file names without generating audio files"
    )

    # Optional force processing flag
    parser.add_argument(
        '--force',
        action='store_true',
        help="Force processing even if input hasn't changed"
    )

    return parser.parse_args()

def calculate_file_hash(file_path: str) -> str:
    """
    Calculate MD5 hash of a file.

    Args:
        file_path (str): Path to the file

    Returns:
        str: MD5 hash of the file content
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""

def get_cache_file_path(workspace_dir: str) -> str:
    """
    Get the path to the cache file that stores input hash.

    Args:
        workspace_dir (str): Workspace directory path

    Returns:
        str: Path to cache file
    """
    return os.path.join(workspace_dir, '.tts_cache')

def load_cached_hash(cache_file_path: str) -> str:
    """
    Load the cached input hash.

    Args:
        cache_file_path (str): Path to cache file

    Returns:
        str: Cached hash or empty string if no cache exists
    """
    try:
        with open(cache_file_path, 'r') as f:
            cache_data = json.load(f)
            return cache_data.get('input_hash', '')
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return ""

def save_cached_hash(cache_file_path: str, input_hash: str):
    """
    Save the input hash to cache file.

    Args:
        cache_file_path (str): Path to cache file
        input_hash (str): Hash to save
    """
    cache_data = {
        'input_hash': input_hash,
        'timestamp': os.path.getctime(cache_file_path) if os.path.exists(cache_file_path) else None
    }
    with open(cache_file_path, 'w') as f:
        json.dump(cache_data, f, indent=2)

def should_skip_processing(input_path: str, output_path: str, cache_file_path: str, force: bool) -> bool:
    """
    Determine if processing should be skipped based on input changes.

    Args:
        input_path (str): Path to input file
        output_path (str): Path to output file
        cache_file_path (str): Path to cache file
        force (bool): Force processing flag

    Returns:
        bool: True if processing should be skipped
    """
    if force:
        return False

    # Check if output file exists
    if not os.path.exists(output_path):
        return False

    # Calculate current input hash
    current_hash = calculate_file_hash(input_path)
    if not current_hash:
        return False

    # Load cached hash
    cached_hash = load_cached_hash(cache_file_path)

    # Compare hashes
    return current_hash == cached_hash

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
    audio_output: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Convert the input project JSON by processing TTS.

    Args:
        input_json (Dict[str, Any]): Input project configuration
        audio_output (str): Output directory for audio files
        dry_run (bool): If True, only print text and filenames without generating audio

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
            if not dry_run:
                # Process the clip
                processed_clip = process_vclip(clip, output_dir)
                processed_clips.append(processed_clip)
            else:
                # In dry-run mode, just extract and print the text and filename
                tts_filename = dryrun_filename(clip)
                if tts_filename:
                    processed_clips.append(tts_filename)

        except ValueError as e:
            raise ValueError(f"Error processing clip {clip_index}: {e}")

    if not dry_run:
        # Create a copy of the input JSON with processed clips
        processed_json = input_json.copy()
        processed_json['vclips'] = processed_clips
    else:
        # dry-run mode
        processed_json = processed_clips

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
        cache_file_path = get_cache_file_path(workspace_dir)

        # Check if processing should be skipped
        if should_skip_processing(input_path, output_path, cache_file_path, args.force):
            print("Input hasn't changed since last processing. Skipping TTS generation.")
            print(f"Use --force to override this behavior.")
            print(f"Input:  {input_path}")
            print(f"Output: {output_path} (existing)")
            print(f"Audio:  {os.path.abspath(args.audio_output)} (existing)")
            return

        # Read input JSON
        try:
            with open(input_path, 'r') as f:
                input_json = json.load(f)
        except FileNotFoundError:
            print(f"Error: Input file {input_path} not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {input_path}")
            sys.exit(1)

        # Convert the project
        try:
            output_json = convert_tts_project(
                input_json,
                audio_output=args.audio_output,
                dry_run=args.dry_run
            )
        except ValueError as e:
            # Detailed error handling for conversion failures
            print(f"Conversion Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error during conversion: {e}")
            sys.exit(1)

        # Write output JSON
        try:
            if args.dry_run:
                with open(output_path, 'w') as f:
                    json.dump(output_json, f, indent=2)
                print("Dry run completed:")
            else:
                with open(output_path, 'w') as f:
                    json.dump(output_json, f, indent=2)
                print("Conversion successful:")

            print(f"Input:  {input_path}")
            print(f"Output: {output_path}")
            print(f"Audio:  {os.path.abspath(args.audio_output)}")

            # Save the current input hash to cache
            current_hash = calculate_file_hash(input_path)
            save_cached_hash(cache_file_path, current_hash)

        except Exception as e:
            print(f"Error writing output file: {e}")
            sys.exit(1)

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()