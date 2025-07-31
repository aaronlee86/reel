import os
import json
import logging
from typing import Dict, Any, List
from mutagen import File

class AudioDurationExtractor:
    @staticmethod
    def get_audio_duration(audio_file_path: str) -> float:
        """
        Extract audio duration from a file.

        Args:
            audio_file_path (str): Path to the audio file

        Returns:
            float: Duration of the audio in seconds

        Raises:
            FileNotFoundError: If audio file does not exist
            ValueError: If audio metadata cannot be read
            RuntimeError: For other processing errors
        """
        # Check file existence
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        try:
            audio = File(audio_file_path)
            if audio is not None:
                return audio.info.length
            else:
                raise ValueError(f"Could not read audio file metadata: {audio_file_path}")
        except Exception as e:
            raise RuntimeError(f"Error processing audio file {audio_file_path}: {e}")

class JSONTransformer:
    @staticmethod
    def validate_input_json(input_json: Dict[str, Any]) -> None:
        """
        Validate input JSON structure.

        Args:
            input_json (Dict[str, Any]): Input JSON to validate

        Raises:
            ValueError: If JSON structure is invalid
        """
        # Basic validation
        if 'vclips' not in input_json:
            raise ValueError("Input JSON must contain 'vclips' key")

        if not isinstance(input_json['vclips'], list):
            raise ValueError("'vclips' must be a list")

    @classmethod
    def transform_json(
        cls,
        input_json: Dict[str, Any],
        audio_folder: str,
        video_folder: str
    ) -> Dict[str, Any]:
        """
        Transform input JSON by calculating start times and durations.

        Args:
            input_json (Dict[str, Any]): Input JSON to transform
            audio_folder (str): Folder containing audio files
            video_folder (str): Folder containing video files

        Returns:
            Dict[str, Any]: Transformed JSON with events
        """
        # Validate input
        cls.validate_input_json(input_json)

        # Create a copy of the input JSON to preserve original
        output_json = input_json.copy()

        # Replace 'vclips' with 'events'
        output_json['events'] = []

        # Track cumulative start time
        current_start_time = 0.0

        # Process each clip
        for vclip in input_json['vclips']:
            # Create a copy of the current clip
            event = vclip.copy()

            # Determine duration
            if 'duration' in event:
                duration = event['duration']
            else:
                # Determine duration based on type
                if event['type'] == 'video':
                    # Use video_folder to locate video file
                    video_path = os.path.join(video_folder, event['file'])
                    duration = AudioDurationExtractor.get_audio_duration(video_path)
                elif event['type'] in ['image', 'text']:
                    # Use audio_folder to locate audio file
                    if 'audio' not in event:
                        raise ValueError(f"No audio specified for {event['type']} clip")

                    audio_path = os.path.join(audio_folder, event['audio'])
                    duration = AudioDurationExtractor.get_audio_duration(audio_path)
                else:
                    raise ValueError(f"Unsupported clip type: {event['type']}")

            # Create a new event dictionary with 'start' first, then 'duration'
            transformed_event = {
                'start': current_start_time,
                'duration': duration
            }

            # Add all original event properties
            transformed_event.update(event)

            # Add to events and update start time
            output_json['events'].append(transformed_event)
            current_start_time += duration

        # Remove original vclips
        del output_json['vclips']

        return output_json

class TtsClipProcessor:
    @staticmethod
    def process_json_file(
        input_file: str,
        output_file: str,
        audio_folder: str,
        video_folder: str,
        verbose: bool = False
    ) -> None:
        """
        Process JSON file by transforming vclips to events.

        Args:
            input_file (str): Path to input JSON file
            output_file (str): Path to output JSON file
            audio_folder (str): Folder containing audio files
            video_folder (str): Folder containing video files
            verbose (bool): Enable verbose logging
        """
        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Processing input file: {input_file}")

            # Read input JSON
            with open(input_file, 'r') as f:
                input_json = json.load(f)

            # Transform JSON
            output_json = JSONTransformer.transform_json(
                input_json,
                audio_folder=audio_folder,
                video_folder=video_folder
            )

            # Write output JSON
            with open(output_file, 'w') as f:
                json.dump(output_json, f, indent=2)

            logger.info(f"JSON transformation completed. Output written to: {output_file}")

        except Exception as e:
            logger.error(f"Error during JSON transformation: {e}")
            raise