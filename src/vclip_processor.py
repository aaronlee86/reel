import os
from typing import Dict, Any

from src.tts.base import TTSEngine
from src.tts.dummy_tts import DummyTTSEngine
from src.tts.gcloud_tts import GoogleCloudTTSEngine
from src.tts.elevenlabs import ElevenLabsTTSEngine
from src.tts.engine_factory import TTSEngineFactory
from src.tts.openai import OpenAiTTSEngine
from src.tts.gemini import GeminiTTSEngine

def process_vclip(
    clip: Dict[str, Any],
    output_dir: str = 'generated_audio'
) -> Dict[str, Any]:
    """
    Process a single video clip configuration.

    Args:
        clip (Dict[str, Any]): Video clip configuration
        output_dir (str, optional): Directory to save generated audio files.
            Defaults to 'generated_audio'.

    Returns:
        Dict[str, Any]: Processed clip configuration
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create a copy of the clip to avoid modifying the original
    processed_clip = clip.copy()

    # Determine clip type
    clip_type = processed_clip.get('type', '')

    # Process based on clip type
    if clip_type == 'text':
        # For text clips, always process TTS
        processed_clip = _process_text_clip(
            processed_clip,
            output_dir
        )
    elif clip_type == 'image':
        # For image clips, handle audio based on specific conditions
        processed_clip = _process_image_clip(
            processed_clip,
            output_dir
        )

    return processed_clip

def _validate_tts_config(tts_config: Dict[str, Any]) -> None:
    """
    Validate TTS configuration for required attributes.

    Args:
        tts_config (Dict[str, Any]): TTS configuration dictionary

    Raises:
        ValueError: If required attributes are missing
    """
    # Check for required attributes
    required_attrs = ['text', 'tts_engine', 'voice']
    for attr in required_attrs:
        if attr not in tts_config:
            raise ValueError(f"Missing required TTS attribute: {attr}")

    # Ensure text is not empty
    if not tts_config['text'].strip():
        raise ValueError("TTS text cannot be empty")

def _process_text_clip(
    clip: Dict[str, Any],
    output_dir: str
) -> Dict[str, Any]:
    """
    Process audio for text clip configuration.

    Args:
        clip (Dict[str, Any]): Video clip configuration
        output_dir (str): Directory to save generated audio files

    Returns:
        Dict[str, Any]: Processed clip configuration
    """
    # Check if TTS configuration exists
    if 'tts' not in clip:
        return clip

    # Prepare text for TTS
    tts_config = clip['tts']

    try:
        # Validate TTS configuration
        _validate_tts_config(tts_config)

        # Set default speed if not provided
        if 'speed' not in tts_config:
            tts_config['speed'] = 1.0

        # Create TTS engine
        tts_engine = TTSEngineFactory.create_engine(tts_config)

        # Generate audio file path
        audio_filename = tts_engine.gen_filename(
            **{k: v for k, v in tts_config.items()}
        )
        audio_path = os.path.join(output_dir, audio_filename)

        # Generate audio using TTS engine
        generated_path = tts_engine.generate_audio(
            text=tts_config['text'],
            output_path=audio_path,
            **{k: v for k, v in tts_config.items() if k != 'text'}
        )

        # Create new dictionary with controlled order
        new_clip = {k: v for k, v in clip.items() if k != 'tts'}
        new_clip['audio'] = os.path.basename(generated_path)

        return new_clip
    except ValueError as e:
        raise ValueError(f"TTS Configuration Error: {e}")
    except Exception as e:
        raise ValueError(f"Error generating audio for text clip: {e}")

def _process_image_clip(
    clip: Dict[str, Any],
    output_dir: str
) -> Dict[str, Any]:
    """
    Process audio for image clip configuration.

    Args:
        clip (Dict[str, Any]): Video clip configuration
        output_dir (str): Directory to save generated audio files

    Returns:
        Dict[str, Any]: Processed clip configuration
    """
    # Create new dictionary with controlled order
    new_clip = {k: v for k, v in clip.items() if k != 'audio'}

    # Check if audio configuration exists
    if 'audio' in clip:
        audio_config = clip['audio']

        # If 'tts' is inside audio configuration
        if 'tts' in audio_config:
            tts_config = audio_config['tts']

            try:
                # Validate TTS configuration
                _validate_tts_config(tts_config)

                # Set default speed if not provided
                if 'speed' not in tts_config:
                    tts_config['speed'] = 1.0

                # Create TTS engine
                tts_engine = TTSEngineFactory.create_engine(tts_config)

                # Generate audio file path
                audio_filename = tts_engine.gen_filename(
                    **{k: v for k, v in tts_config.items()}
                )

                audio_path = os.path.join(output_dir, audio_filename)

                # Generate audio using TTS engine
                generated_path = tts_engine.generate_audio(
                    text=tts_config['text'],
                    output_path=audio_path,
                    **{k: v for k, v in tts_config.items() if k != 'text'}
                )

                # Add audio attribute with generated filename
                new_clip['audio'] = os.path.basename(generated_path)
            except ValueError as e:
                raise ValueError(f"TTS Configuration Error: {e}")
            except Exception as e:
                raise Exception(f"Error generating audio for image clip: {e}")

        # If 'file' is inside audio configuration
        elif 'file' in audio_config:
            new_clip['audio'] = audio_config['file']

    return new_clip

def _find_tts_attr(data):
    """
    Find any attribute called 'tts' in a dictionary and return its value.
    Works with nested dictionary structures.

    Args:
        data (dict): Dictionary to search

    Returns:
        dict or None: The value of the 'tts' attribute if found, None otherwise
    """
    # Check if 'tts' key exists at current level
    if 'tts' in data:
        return data['tts']

    # Recursively search in nested dictionaries
    for value in data.values():
        if isinstance(value, dict):
            result = _find_tts_attr(value)
            if result is not None:
                return result
        elif isinstance(value, list):
            # Handle lists that might contain dictionaries
            for item in value:
                if isinstance(item, dict):
                    result = _find_tts_attr(item)
                    if result is not None:
                        return result

    return None


def dryrun_filename(
        clip: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate TTS filename for a clip configuration.

    Args:
        clip: Dictionary containing clip configuration

    Returns:
        Updated TTS configuration with filename, or None if no TTS config found
    """
    tts_config = _find_tts_attr(clip)
    if tts_config is None:
        return None

    # Validate TTS configuration
    _validate_tts_config(tts_config)

    # Create TTS engine
    tts_engine = TTSEngineFactory.create_engine(tts_config)

    # Generate audio file path
    audio_filename = tts_engine.gen_filename(
        **{k: v for k, v in tts_config.items()}
    )

    # Add filename to config and return
    tts_config['filename'] = audio_filename
    return tts_config
