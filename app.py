from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import datetime
import os
import tempfile
import moviepy
print(f"MoviePy version: {moviepy.__version__}")
from moviepy.editor import ImageSequenceClip
import logging
import pytz

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET'])
def home():
    return '''
    <h2>Upload your ticket</h2>
    <form method="post" enctype="multipart/form-data" action="/generate">
        <input type="file" name="file">
        <input type="submit">
    </form>
    '''

@app.route('/generate', methods=['POST'])
def generate():
    try:
        logging.debug("Starting generate function")
        file = request.files['file']
        img = Image.open(file.stream).convert("RGB")
        logging.debug(f"Image loaded, size: {img.size}")
        
        w, h = img.size
        frames = []
        # Use NJ timezone (America/New_York)
        nj_tz = pytz.timezone('America/New_York')
        base_time = datetime.datetime.now(nj_tz)

        try:
            font = ImageFont.truetype("Roboto-SemiBold.ttf", 60)
            logging.debug("Font loaded successfully")
        except IOError as e:
            font = ImageFont.load_default().font_variant(size=60)
            logging.debug(f"Font load failed, using default: {e}")

        timestamp_pos = (w // 2 - 200, h - 600)
        timestamp_bbox = [0, h - 650, w, h - 450]
        expires_pos = (w // 2 - 150, h - 360)
        expires_bbox = [0, h - 350, w, h - 250]
        bar_bbox = [0, h - 440, w, h - 355]
        # Approximate area for the big "1" (adjust based on your screenshot)
        number_bbox = [w // 2 - 100, h - 1750, w // 2 + 100, h - 1525]  # Example; refine with measurement

        # Create a "2" image with matching size and font
        number_font = ImageFont.truetype("Roboto-ExtraBold.ttf", 240)  # Match the "1" size
        number_text = "2"
        number_img = Image.new("RGBA", (number_bbox[2] - number_bbox[0], number_bbox[3] - number_bbox[1]), (0, 0, 0, 0))
        number_draw = ImageDraw.Draw(number_img)
        bbox = number_draw.textbbox((0, 0), number_text, font=number_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (number_img.width - text_width) // 2
        y = (number_img.height - text_height) // 2 - 60  # Move up by 30 pixels; adjust as needed
        number_draw.text((x, y), number_text, fill=(0, 0, 0, 255), font=number_font)

        # Load reference image with red "INTERSTATE" and prepare for pasting
        reference_path = os.path.join(os.path.dirname(__file__), "interstate.png")
        if os.path.exists(reference_path):
            reference_img = Image.open(reference_path).convert("RGBA")
            logging.debug(f"Reference image loaded, size: {reference_img.size}")
            # Define the exact coordinates of "INTERSTATE" in the reference image (adjust based on your screenshot)
            interstate_x1, interstate_y1 = 0, h-1950  # Example coordinates; replace with actual values
            interstate_x2, interstate_y2 = w, h-1780  # Example coordinates; replace with actual values
            interstate_crop = reference_img.crop((interstate_x1, interstate_y1, interstate_x2, interstate_y2))
            interstate_width = interstate_x2 - interstate_x1
            interstate_height = interstate_y2 - interstate_y1
        else:
            logging.error("Reference image interstate_reference.png not found")
            return "Reference image not found", 500

        for i in range(40):
            frame = img.copy()
            draw = ImageDraw.Draw(frame)

            # Draw timestamp rectangle (white box)
            draw.rectangle(timestamp_bbox, fill="white")
            current_time = base_time + datetime.timedelta(seconds=i)
            timestamp_text = current_time.strftime("%I:%M:%S %p\n%A, %b %d, %Y")
            timestamp_lines = timestamp_text.split('\n')
            y_offset = timestamp_pos[1]
            for idx, line in enumerate(timestamp_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                x = w // 2 - line_width // 2
                if idx == 0:
                    draw.text((x, y_offset), line, fill="black", font=font)
                else:
                    extra_spacing = 6
                    draw.text((x, y_offset + (idx * (bbox[3] - bbox[1])) + extra_spacing), line, fill="black", font=font)

            # Draw expires rectangle (white box)
            draw.rectangle(expires_bbox, fill="white")
            remaining_seconds = 3600 - i
            minutes, seconds = divmod(remaining_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            expires_text = f"Expires in 00:{hours:02d}:{minutes:02d}:{seconds:02d}"
            expires_lines = expires_text.split('\n')
            y_offset = expires_pos[1]
            for idx, line in enumerate(expires_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                x = w // 2 - line_width // 2
                if idx == 0:
                    draw.text((x, y_offset), line, fill="black", font=font)
                else:
                    extra_spacing = 20
                    draw.text((x, y_offset + (idx * (bbox[3] - bbox[1])) + extra_spacing), line, fill="black", font=font)

            # Replace "1" with "2" using a copied gradient patch
            number_width = number_bbox[2] - number_bbox[0]
            number_height = number_bbox[3] - number_bbox[1]
            patch_x = number_bbox[0] - number_width
            if patch_x < 0:
                patch_x = number_bbox[0] + number_width
            patch = img.crop((patch_x, number_bbox[1], patch_x + number_width, number_bbox[3]))
            frame.paste(patch, number_bbox)
            if number_img.mode != "RGBA":
                number_img = number_img.convert("RGBA")
            frame.paste(number_img, number_bbox, number_img)

            # Paste red "INTERSTATE" at the same absolute coordinates
            frame.paste(interstate_crop, (interstate_x1, interstate_y1), interstate_crop)

            if i % 2 != 0:
                draw.rectangle(bar_bbox, fill="white")

            frames.append(np.array(frame))

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            out_path = tmp_file.name

        logging.debug(f"Starting video write to {out_path}")
        clip = ImageSequenceClip(frames, fps=1)
        clip.write_videofile(out_path, codec="mpeg4", audio=False, verbose=True, logger='bar')
        logging.debug(f"Video written, size: {os.path.getsize(out_path)} bytes")

        response = send_file(out_path, mimetype="video/mp4", as_attachment=True, download_name="ticket_video.mp4")
        @response.call_on_close
        def cleanup():
            try:
                os.remove(out_path)
            except OSError:
                pass

        return response

    except Exception as e:
        logging.error(f"Error in generate: {str(e)}")
        return f"Error generating video: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)