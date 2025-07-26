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
        valign: str,
        halign: str,
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

    def _calculate_x_position(
        self,
        text: str,
        font_size: int,
        screen_width: int,
        halign: str,
        padding: int
    ) -> int:
        """
        Calculate x position based on horizontal alignment

        Args:
            text (str): Text to position
            font_size (int): Font size
            screen_width (int): Screen width
            halign (str): Horizontal alignment
            padding (int): Padding from screen edges

        Returns:
            int: Calculated x position
        """
        # Validate horizontal alignment
        if halign not in ['left', 'center', 'right']:
            raise ValueError(f"Invalid halign value: {halign}. Must be 'left', 'center', or 'right'.")

        # Placeholder width calculation
        estimated_text_width = len(text) * (font_size * 0.5)

        # Calculate x position
        if halign == 'left':
            return padding
        elif halign == 'right':
            return screen_width - estimated_text_width - padding
        else:  # center
            return (screen_width - estimated_text_width) // 2

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