import os
from PIL import Image, ImageDraw, ImageFont

def render_text_block(
    text_lines: list[str],
    positions: list[tuple[int, int]],
    font_paths: list[str],
    font_sizes: list[int],
    font_colors: list[str],
    bold_flags: list[bool],
    italic_flags: list[bool],
    bg_color: str,
    size: tuple[int, int],
    background_image: Image.Image | None = None
) -> Image.Image:
    """
    Renders multiple lines of text with individual styling onto an image.

    Args:
        text_lines (list): List of strings, each representing a line of text to render
        positions (list): List of (x, y) tuples specifying the position for each text line
        font_paths (list): List of path to the font files (e.g., "Arial.ttf")
        font_sizes (list): List of font sizes for each text line
        font_colors (list): List of color values for each text line (hex strings or color names)
        bold_flags (list): List of booleans indicating whether each line should be bold
        italic_flags (list): List of booleans indicating whether each line should be italic
        bg_color (str, optional): Background color for new images.
        size (tuple, optional): Image dimensions as (width, height).
        background_image (PIL.Image, optional): Existing image to draw on. If None, creates new image

    Returns:
        PIL.Image: The rendered image with text applied
    """
    if background_image:
        img = background_image.copy()
    else:
        img = Image.new("RGB", size, color=bg_color)

    draw = ImageDraw.Draw(img)

    for i, line in enumerate(text_lines):
        x, y = positions[i]
        font_size = font_sizes[i]
        color = font_colors[i]
        bold = bold_flags[i]
        italic = italic_flags[i]

        actual_font_path = font_paths[i]
        font_style_tag = ""
        if bold and italic:
            font_style_tag = "-BoldItalic"
        elif bold:
            font_style_tag = "-Bold"
        elif italic:
            font_style_tag = "-Italic"

        if font_style_tag:
            base, ext = os.path.splitext(actual_font_path)
            styled_path = f"{base}{font_style_tag}{ext}"
            if os.path.exists(styled_path):
                actual_font_path = styled_path

        try:
            font = ImageFont.truetype(actual_font_path, font_size)
        except Exception:
            font = ImageFont.load_default()

        draw.text((x, y), line, font=font, fill=color)

    return img
