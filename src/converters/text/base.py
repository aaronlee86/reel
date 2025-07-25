from abc import ABC, abstractmethod
from typing import Dict, Any, List

class TextSceneStrategy(ABC):
    """
    Abstract base class for text scene conversion strategies
    """
    @abstractmethod
    def calculate_text_positions(
        self, 
        text_entries: List[Dict[str, Any]], 
        screen_size: List[int],
        valign: str = 'center',
        padding: int = 40,
        line_spacing: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Calculate positions for text entries
        
        Args:
            text_entries (List[Dict[str, Any]]): List of text entries
            screen_size (List[int]): Screen dimensions [width, height]
            valign (str): Vertical alignment
            padding (int): Vertical padding
            line_spacing (int): Space between lines
        
        Returns:
            List[Dict[str, Any]]: Text entries with calculated positions
        """
        pass

    @abstractmethod
    def convert(
        self, 
        scene: Dict[str, Any], 
        positioned_entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert text scene using specific strategy
        
        Args:
            scene (Dict[str, Any]): Scene configuration
            positioned_entries (List[Dict[str, Any]]): Positioned text entries
        
        Returns:
            List[Dict[str, Any]]: Generated virtual clips
        """
        pass