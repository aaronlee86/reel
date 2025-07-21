from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class SceneConverter(ABC):
    """Abstract base class for scene converters"""
    def __init__(
        self,
        screen_size: Optional[List[int]] = None,
        fps: int = 24,
        default_duration: float = 3.0
    ):
        """
        Initialize base converter

        Args:
            screen_size (Optional[List[int]]): Screen dimensions [width, height]
            fps (int): Frames per second
            default_duration (float): Default clip duration if not specified
        """
        self.screen_size = screen_size or [1920, 1080]
        self.fps = fps
        self.default_duration = default_duration

    @abstractmethod
    def convert(self, scene: Dict[str, Any], project_name: str = 'default') -> List[Dict[str, Any]]:
        """
        Convert a specific scene type to virtual clips

        Args:
            scene (Dict[str, Any]): Input scene dictionary
            project_name (str): Name of the current project

        Returns:
            List[Dict[str, Any]]: List of virtual clips generated from the scene
        """
        pass