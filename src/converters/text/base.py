from abc import ABC, abstractmethod
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont


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
        font_path: str,
        screen_width: int,
        halign: str,
        padding: int
    ) -> int:
        """
        Calculate x position based on horizontal alignment with accurate text measurement

        Args:
            text (str): Text to position
            font_size (int): Font size in points
            screen_width (int): Screen width in pixels
            halign (str): Horizontal alignment ('left', 'center', or 'right')
            padding (int): Padding from screen edges in pixels
            font_path (str): Path to the font file (required)

        Returns:
            int: Calculated x position

        Raises:
            ValueError: If halign is invalid or font_path is not provided
            FileNotFoundError: If font file doesn't exist
            OSError: If font file is invalid or corrupted
        """
        # Validate horizontal alignment
        if halign not in ['left', 'center', 'right']:
            raise ValueError(f"Invalid halign value: {halign}. Must be 'left', 'center', or 'right'.")

        # Validate font_path is provided
        if not font_path:
            raise ValueError("font_path is required. Please provide a valid path to a font file.")

        try:
            # Load the font
            font = ImageFont.truetype(font_path, font_size)
        except FileNotFoundError:
            raise FileNotFoundError(f"Font file not found: {font_path}")
        except OSError as e:
            raise OSError(f"Invalid or corrupted font file '{font_path}': {str(e)}")

        # Create dummy image for measurement
        img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(img)

        # Get actual text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        # Calculate position based on alignment
        if halign == 'left':
            return padding
        elif halign == 'right':
            return screen_width - text_width - padding
        else:  # center
            return (screen_width - text_width) // 2

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

    def clean_attributes(self, sentence):
        """
        Remove 'tts' and 'halign' from sentences in virtual clips

        Args:
            positioned_sentences (List[Dict]): List of virtual clips to clean

        Returns:
            List[Dict]: Cleaned virtual clips
        """
        try:
            # Create a copy of the sentence, excluding 'tts' and 'halign'
            cleaned_sentence = {
                k: v for k, v in sentence.items()
                if k not in ['tts', 'halign']
            }
            return cleaned_sentence
        except Exception as e:
            raise Exception(f"clean_attributes error {e}")