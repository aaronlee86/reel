from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
from PIL import Image, ImageDraw, ImageFont
import unicodedata
import re
import copy


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
        v_padding: int,
        h_padding: int,
        para_spacing: int,
        line_spacing: int
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

    from PIL import Image, ImageDraw, ImageFont

    def _calculate_x_position(
        self,
        text: str,
        font_size: int,
        font_path: str,
        screen_width: int,
        halign: str,
        padding: int,
        wrap: bool = True,
        min_font_size: int = 1
    ) -> tuple[int, int, int, str]:
        """
        Calculate x position based on horizontal alignment with automatic font scaling
        Args:
            text (str): Text to position
            font_size (int): Desired font size in points
            font_path (str): Path to the font file
            screen_width (int): Screen width in pixels
            halign (str): Horizontal alignment ('left', 'center', or 'right')
            padding (int): Padding from screen edges in pixels
            min_font_size (int): Minimum allowed font size (default: 1)
        Returns:
            tuple[int, int, int, str]: (x_position, height, actual_font_size_used, wrapped_text)
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

        # Create dummy image for measurement (move outside loop)
        img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(img)

        final_text = text
        # Try to find largest font size that fits
        while current_font_size >= min_font_size:
            try:
                font = ImageFont.truetype(font_path, current_font_size)
                if wrap:
                    final_text = self.wrap_text(text, font, available_width)
            except FileNotFoundError:
                raise FileNotFoundError(f"Font file not found: {font_path}")
            except OSError as e:
                raise OSError(f"Invalid or corrupted font file '{font_path}': {str(e)}")

            # Get actual text dimensions
            bbox = draw.textbbox((0, 0), final_text, font=font)
            text_width = bbox[2] - bbox[0]

            # If it fits, use this font size
            if text_width <= available_width:
                break
            current_font_size -= 1

        # If even minimum font size doesn't fit, use minimum anyway
        if current_font_size < min_font_size:
            current_font_size = min_font_size
            font = ImageFont.truetype(font_path, current_font_size)

        # Get final text dimensions for positioning
        bbox = draw.textbbox((0, 0), final_text, font=font)
        text_width = bbox[2] - bbox[0]

        # Calculate position based on alignment
        if halign == 'left':
            x_position = padding
        elif halign == 'right':
            x_position = screen_width - padding - text_width
        else:  # center
            x_position = (screen_width - text_width) // 2

        return x_position, bbox[3]-bbox[1], current_font_size, final_text

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
            # Create a copy of the sentence, excluding attributs in the list
            cleaned_sentence = {
                k: v for k, v in sentence.items()
                if k not in ['tts', 'halign', 'pregap', 'postgap', 'duration']
            }
            return cleaned_sentence
        except Exception as e:
            raise Exception(f"clean_attributes error {e}")

    def _detect_script_type(self, text: str) -> str:
        """
        Detect the primary script type of the text
        Returns 'cjk' for Chinese/Japanese/Korean, 'other' for other scripts
        """
        # Handle empty string case
        if not text:
            return 'other'

        # Check if text contains CJK (Chinese/Japanese/Korean) characters
        cjk_chars = sum(1 for char in text if unicodedata.category(char).startswith('Lo') and
                        ('\u4E00' <= char <= '\u9FFF' or  # CJK Unified Ideographs
                            '\u3040' <= char <= '\u30FF' or  # Hiragana and Katakana
                            '\uAC00' <= char <= '\uD7A3'))   # Korean Hangul

        # If more than 50% of characters are CJK, consider it a CJK script
        return 'cjk' if cjk_chars / len(text) > 0.5 else 'other'

    def wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        """
        Wrap text to fit within max width
        Handles different script types intelligently
        """
        # Handle empty or None input
        if not text:
            return ''

        # Create a temporary image for text size calculations
        img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(img)

        wrapped_lines = []
        script_type = self._detect_script_type(text)

        # Split the text into paragraphs first
        paragraphs = text.split('\n')

        for paragraph in paragraphs:
            # Skip empty paragraphs
            if not paragraph:
                wrapped_lines.append('')
                continue

            if script_type == 'cjk':
                # Character-based wrapping for CJK scripts
                wrapped_lines.extend(self._wrap_cjk_text(paragraph, draw, font, max_width))
            else:
                # Word-based wrapping for other scripts
                wrapped_lines.extend(self._wrap_word_text(paragraph, draw, font, max_width))

        return '\n'.join(wrapped_lines)

    def _wrap_cjk_text(self, text: str, draw, font, max_width: int) -> list:
        """
        Wrap CJK text character by character
        """
        wrapped_lines = []
        current_line = []
        current_line_width = 0

        for char in text:
            # Calculate character width
            char_width = draw.textlength(char, font=font)

            # Check if adding this character would exceed max width
            if current_line:
                test_line_width = current_line_width + char_width
                if test_line_width > max_width:
                    # Add current line to wrapped lines
                    wrapped_lines.append(''.join(current_line))
                    current_line = [char]
                    current_line_width = char_width
                else:
                    # Add character to current line
                    current_line.append(char)
                    current_line_width = test_line_width
            else:
                # First character of a new line
                current_line = [char]
                current_line_width = char_width

        # Add the last line if not empty
        if current_line:
            wrapped_lines.append(''.join(current_line))

        return wrapped_lines

    def _wrap_word_text(self, text: str, draw, font, max_width: int) -> list:
        """
        Wrap text for non-CJK scripts using intelligent word wrapping
        """
        wrapped_lines = []
        current_line = []
        current_line_width = 0

        # Use regex to split text into tokens (words, punctuation, etc.)
        tokens = re.findall(r'\S+|\s+', text)

        for token in tokens:
            # Calculate token width
            token_width = draw.textlength(token, font=font)

            # Check if adding this token would exceed max width
            if current_line:
                test_line = ''.join(current_line) + token
                test_line_width = draw.textlength(test_line, font=font)

                if test_line_width > max_width:
                    # Add current line to wrapped lines
                    wrapped_lines.append(''.join(current_line).rstrip())

                    # Special handling for very long tokens that exceed max_width
                    if token_width > max_width:
                        # Break long tokens (like URLs or very long words)
                        wrapped_lines.extend(self._break_long_token(token, draw, font, max_width))
                        current_line = []
                        current_line_width = 0
                    else:
                        # Start a new line with this token
                        current_line = [token]
                        current_line_width = token_width
                else:
                    # Add token to current line
                    current_line.append(token)
                    current_line_width = test_line_width
            else:
                # First token of a new line
                current_line = [token]
                current_line_width = token_width

        # Add the last line if not empty
        if current_line:
            wrapped_lines.append(''.join(current_line).rstrip())

        return wrapped_lines

    def _break_long_token(self, token: str, draw, font, max_width: int) -> list:
        """
        Break an extremely long token into multiple lines
        """
        broken_lines = []
        current_segment = ''

        for char in token:
            test_segment = current_segment + char
            if draw.textlength(test_segment, font=font) <= max_width:
                current_segment = test_segment
            else:
                broken_lines.append(current_segment)
                current_segment = char

        # Add the last segment if not empty
        if current_segment:
            broken_lines.append(current_segment)

        return broken_lines

    def _prepare_text_entry(
        self,
        entry: Dict[str, Any],
        halign: str,
        screen_width: int,
        h_padding: Union[int, float]
    ) -> Dict[str, Union[Dict[str, Any], int, float, str]]:
        """
        Prepare a single text entry with positioning calculations.

        Calculates the horizontal position, height, and adjusted font size for a text entry
        based on its content, font properties, and alignment settings. Also handles text
        wrapping and adjustment if needed.

        Args:
            entry (Dict[str, Any]): Dictionary containing text entry data with keys:
                - 'text' (str): The text content to be positioned
                - 'font' (Dict[str, Any]): Dictionary with 'size' and 'file' keys
                - 'halign' (str, optional): Horizontal alignment override for this entry
            halign (str): Default horizontal alignment ('left', 'center', 'right')
            screen_width (int): Available screen width in pixels for positioning
            h_padding (Union[int, float]): Horizontal padding to apply during calculations

        Returns:
            Dict[str, Union[Dict[str, Any], int, float, str]]: Dictionary containing:
                - 'entry' (Dict[str, Any]): Updated entry dictionary with final text
                - 'x' (Union[int, float]): Calculated x-position for the text
                - 'height' (Union[int, float]): Calculated height of the text
                - 'adjusted_fontsize' (Union[int, float]): Final font size after adjustments
                - 'halign' (str): The horizontal alignment used for this entry

        Raises:
            KeyError: If required keys ('text', 'font') are missing from entry dictionary
            ValueError: If invalid alignment values are provided
            TypeError: If font dictionary doesn't contain required 'size' and 'file' keys
        """
        entry_halign: str = entry.get('halign', halign)
        font: Dict[str, Any] = entry['font']

        x: Union[int, float]
        height: Union[int, float]
        adjusted_fontsize: Union[int, float]
        final_text: str

        x, height, adjusted_fontsize, final_text = self._calculate_x_position(
            entry['text'],
            font['size'],
            font['file'],
            screen_width,
            entry_halign,
            h_padding
        )

        return {
            'entry': {**entry, 'text': final_text},
            'x': x,
            'height': height,
            'adjusted_fontsize': adjusted_fontsize,
            'halign': entry_halign
        }

    def remove_special_char_for_tts(self, text: str) -> str:
        return text.replace('\n','')

    def _create_vclips(self, txt_entry, scene, positioned_entries):
        if not 'tts' in txt_entry and not 'duration' in txt_entry:
            raise ValueError("Each vclip must have either TTS or duration")

        vclips = []

        vclip = {"type": "text"}

        # Set background color or image
        if 'background' in scene:
            vclip['background'] = scene['background']
        elif 'bgcolor' in scene:
            vclip['bgcolor'] = scene['bgcolor']
        else:
            vclip['bgcolor'] = '#000000'  # Default background

        self._passthrough_properties(vclip, txt_entry, 'duration')
        self._passthrough_properties(vclip, txt_entry, 'pregap')
        self._passthrough_properties(vclip, txt_entry, 'postgap')

        # Add positioned sentences
        vclip['sentences'] = positioned_entries

        if 'tts' in txt_entry:
            for i, tts_entry in enumerate(txt_entry['tts']):
                repeated_vclip = copy.deepcopy(vclip)
                if i > 0:
                    repeated_vclip.pop('pregap', None)
                if i < len(txt_entry['tts'])-1:
                    repeated_vclip.pop('postgap', None)

                if 'pregap' in tts_entry:
                    repeated_vclip['pregap'] = tts_entry['pregap']

                repeated_vclip['tts'] = {
                    "text": self.remove_special_char_for_tts(txt_entry['dub'] if 'dub' in txt_entry else txt_entry['text']),
                    "tts_engine": tts_entry['tts_engine'],
                    "voice": tts_entry['voice'],
                    "speed": tts_entry.get('speed', 1.0)
                }
                vclips.append(repeated_vclip)
        else:
            vclips.append(vclip)

        return vclips

    def _passthrough_properties(self, dest, src, prop):
        if prop in src:
           dest[prop] = src[prop]