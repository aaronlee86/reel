from abc import ABC, abstractmethod
from typing import Dict, Any, List

class SceneConverter(ABC):
    """Abstract base class for scene converters"""
    def __init__(
        self,
        screen_size: List[int],
        fps: int
    ):
        """
        Initialize base converter

        Args:
            screen_size (List[int]): Screen dimensions [width, height]
            fps (int): Frames per second
        """
        self.screen_size = screen_size
        self.fps = fps

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