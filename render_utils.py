from PIL import Image, ImageDraw, ImageFont
import os

def render_text_block(
    text_lines,
    positions,
    font_path,
    font_sizes,
    font_colors,
    bold_flags,
    italic_flags,
    bg_color,
    size
):
    img = Image.new("RGB", size, bg_color)
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(text_lines):
        x, y = positions[i]
        font_size = font_sizes[i]
        color = font_colors[i]
        bold = bold_flags[i]
        italic = italic_flags[i]

        # Determine font style (basic handling)
        actual_font_path = font_path
        font_style_tag = ""
        if bold and italic:
            font_style_tag = "-BoldItalic"
        elif bold:
            font_style_tag = "-Bold"
        elif italic:
            font_style_tag = "-Italic"

        if font_style_tag:
            base, ext = os.path.splitext(font_path)
            styled_path = f"{base}{font_style_tag}{ext}"
            if os.path.exists(styled_path):
                actual_font_path = styled_path

        try:
            font = ImageFont.truetype(actual_font_path, font_size)
        except Exception:
            font = ImageFont.load_default()

        draw.text((x, y), line, font=font, fill=color)

    return img
