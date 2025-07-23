import os
from typing import Dict, Any, List, Optional, Union
from .base import SceneConverter

class VideoSceneConverter(SceneConverter):
    def convert(
        self,
        scene: Dict[str, Any],
        project_name: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        Convert a video scene to virtual clips

        Args:
            scene (Dict[str, Any]): Video scene details
            project_name (str): Name of the current project

        Returns:
            List[Dict[str, Any]]: Virtual clips for the video scene

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate file is specified
        if 'file' not in scene:
            raise ValueError("Video scene must specify a 'file'")

        # Extract basic scene parameters
        file = scene['file']
        start_time = scene.get('start_time', 0)
        duration = scene.get('duration')

        # Validate start_time and duration
        if start_time < 0:
            raise ValueError("Start time cannot be negative")

        if duration is not None and duration < 0:
            raise ValueError("Duration cannot be negative")

        # Prepare video clip
        vclip: Dict[str, Any] = {
            "type": "video",
            "file": file
        }

        # Add start_time if not zero
        if start_time > 0:
            vclip['start_time'] = start_time

        # Add duration if specified
        if duration is not None:
            vclip['duration'] = duration

        return [vclip]
