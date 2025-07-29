import os
import argparse
from src.ttsclip_processor import TtsClipProcessor

def parse_arguments():
    """
    Parse command-line arguments.
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert audio TTS clips JSON to final clips with start and duration"
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
        default='ttsclips.json',
        help="Input scenes JSON filename (default: ttsclips.json)"
    )
    # Optional output file argument
    parser.add_argument(
        '--output',
        type=str,
        default='clips.json',
        help="Output clips JSON filename (default: clips.json)"
    )
    # Optional audio folder argument
    parser.add_argument(
        '--audio-folder',
        type=str,
        default='audio',
        help="Folder containing audio files (default: audio)"
    )
    # Optional video folder argument
    parser.add_argument(
        '--video-folder',
        type=str,
        default='video',
        help="Folder containing video files (default: video)"
    )

    return parser.parse_args()

def main():
    # Parse arguments
    args = parse_arguments()

    # Check if workspace directory exists
    workspace_dir = os.path.join('workspace', args.project)
    if not os.path.exists(workspace_dir):
        raise FileNotFoundError(f"Workspace directory does not exist: {workspace_dir}")

    # Construct full input and output paths
    input_path = os.path.join(workspace_dir, args.input)
    output_path = os.path.join(workspace_dir, args.output)

    # Construct full audio and video folder paths
    audio_folder = os.path.join(workspace_dir, args.audio_folder)
    video_folder = os.path.join(workspace_dir, args.video_folder)

    # Process the JSON file
    TtsClipProcessor.process_json_file(
        input_path,
        output_path,
        audio_folder=audio_folder,
        video_folder=video_folder
    )

if __name__ == '__main__':
    main()