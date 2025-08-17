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
        padding: int,
        min_font_size: int = 1
    ) -> tuple[int, int]:
        """
        Calculate x position based on horizontal alignment with automatic font scaling

        Args:
            text (str): Text to position
            font_size (int): Desired font size in points
            font_path (str): Path to the font file
            screen_width (int): Screen width in pixels
            halign (str): Horizontal alignment ('left', 'center', or 'right')
            padding (int): Padding from screen edges in pixels
            min_font_size (int): Minimum allowed font size (default: 8)

        Returns:
            tuple[int, int]: (x_position, actual_font_size_used)

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

        available_width = screen_width - 2 * padding
        current_font_size = max(font_size, min_font_size)

        # Try to find largest font size that fits
        while current_font_size >= min_font_size:
            try:
                font = ImageFont.truetype(font_path, current_font_size)
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

            # If it fits, use this font size
            if text_width <= available_width:
                break

            current_font_size -= 1

        # If even minimum font size doesn't fit, use minimum anyway
        if current_font_size < min_font_size:
            current_font_size = min_font_size
            font = ImageFont.truetype(font_path, current_font_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]

        # Calculate position based on alignment
        if halign == 'left':
            x_position = padding
        elif halign == 'right':
            x_position = screen_width - text_width - padding
        else:  # center
            x_position = (screen_width - text_width) // 2

        return x_position, current_font_size

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