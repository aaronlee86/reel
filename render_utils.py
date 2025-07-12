from PIL import Image, ImageDraw, ImageFont

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
    img = Image.new("RGB", size, color=bg_color)
    draw = ImageDraw.Draw(img)

    for text, pos, size_px, color, bold, italic in zip(
        text_lines, positions, font_sizes, font_colors, bold_flags, italic_flags
    ):
        try:
            font = ImageFont.truetype(font_path, size_px)
        except OSError:
            raise ValueError(f"Font not found or invalid: {font_path}")

        draw.text(tuple(pos), text, font=font, fill=color)

    return img
