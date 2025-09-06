import os
from typing import Dict, Any, List, Optional, Union
from .base import SceneConverter

class ImageSceneConverter(SceneConverter):
    def convert(
        self,
        scene: Dict[str, Any],
        project_name: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        Convert an image scene to virtual clips
        Args:
            scene (Dict[str, Any]): Image scene details
            project_name (str): Name of the current project
        Returns:
            List[Dict[str, Any]]: Virtual clips for the image scene
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate scene configuration
        if 'file' in scene and 'bgcolor' in scene:
            raise ValueError("Cannot specify both 'file' and 'bgcolor' in an image scene")

        # Check for offset in main section
        if 'offset' in scene:
            raise ValueError("Offset must be specified in the audio section, not in the main scene")

        # Check audio configuration
        audio_config = scene.get('audio', {})

        # Validate audio configuration
        if audio_config:
            # Require either file or tts
            if 'file' not in audio_config and 'tts' not in audio_config:
                raise ValueError("Audio configuration must have either 'file' or 'tts'")

            # Prevent simultaneous file and tts
            if 'file' in audio_config and 'tts' in audio_config:
                raise ValueError("Cannot specify both 'file' and 'tts' in audio configuration")

            # Check for speed outside of TTS
            if 'speed' in audio_config:
                raise ValueError("Speed must be specified inside the TTS configuration")

        # Validate duration based on audio presence
        if not audio_config and 'duration' not in scene:
            raise ValueError("Duration is required for silent scenes")

        # Extract basic scene parameters
        duration = scene.get('duration', None)
        file = scene.get('file')
        bgcolor = scene.get('bgcolor')
        pregap = scene.get('pregap')
        postgap = scene.get('postgap')

        # Ensure at least one of file or bgcolor is specified
        if file is None and bgcolor is None:
            # Default to black background if nothing specified
            bgcolor = '#000000'

        # Prepare base vclip
        vclip: Dict[str, Any] = {
            "type": "image",
        }

        # Add duration if specified
        if duration is not None:
            vclip['duration'] = duration

        # Add file if specified
        if file:
            vclip['file'] = file

        # Add pregap if specified
        if pregap:
            vclip['pregap'] = pregap

        # Add postgap if specified
        if postgap:
            vclip['postgap'] = postgap

        # Add background color if no file
        if bgcolor:
            vclip['bgcolor'] = bgcolor

        # Handle audio
        if audio_config:
            # Add audio details to vclip
            vclip['audio'] = {}

            # Handle file-based audio
            if 'file' in audio_config:
                vclip['audio']['file'] = audio_config['file']

            # Handle TTS
            if 'tts' in audio_config:
                tts_config = audio_config['tts']
                vclip['audio']['tts'] = {
                    'text': tts_config['text'],
                    'tts_engine': tts_config['tts_engine'],
                    'voice': tts_config['voice'],
                    'speed': tts_config.get('speed', 1.0)
                }

        # Handle offset clips
        offset = audio_config.get('offset', 0) if audio_config else 0

        # Generate clips
        if offset > 0:
            # Create a silent clip for the offset
            offset_clip = {
                "type": "image",
                "duration": offset,
            }

            # If file or bgcolor was in original scene, add to offset clip
            if 'file' in vclip:
                offset_clip['file'] = vclip['file']
            if 'bgcolor' in vclip:
                offset_clip['bgcolor'] = vclip['bgcolor']

            # Prepare the second vclip with audio
            audio_vclip = vclip.copy()

            # Adjust duration if specified
            if duration is not None:
                audio_vclip['duration'] = duration - offset

            return [offset_clip, audio_vclip]

        return [vclip]