from abc import ABC, abstractmethod
from typing import Dict, Any, List

class SceneConverter(ABC):
    """Abstract base class for scene converters"""
    @abstractmethod
    def convert(self, scene: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert a specific scene type to virtual clips
        
        Args:
            scene (Dict[str, Any]): Input scene dictionary
        
        Returns:
            List[Dict[str, Any]]: List of virtual clips generated from the scene
        """
        pass
