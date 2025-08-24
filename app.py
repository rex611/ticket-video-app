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
        base_time = datetime.datetime.now()

        try:
            font = ImageFont.truetype("Roboto-SemiBold.ttf", 33.5)
            logging.debug("Font loaded successfully")
        except IOError as e:
            font = ImageFont.load_default().font_variant(size=33.5)
            logging.debug(f"Font load failed, using default: {e}")

        timestamp_pos = (w // 2 - 200, h - 350)
        timestamp_bbox = [w // 2 - 250, h - 400, w // 2 + 250, h - 260]
        expires_pos = (w // 2 - 150, h - 200)
        expires_bbox = [w // 2 - 200, h - 205, w // 2 + 200, h - 150]
        bar_bbox = [0, h - 260, w, h - 205]

        for i in range(60):
            frame = img.copy()
            draw = ImageDraw.Draw(frame)

            draw.rectangle(timestamp_bbox, fill="white")
            current_time = base_time + datetime.timedelta(seconds=i)
            timestamp_text = current_time.strftime("%I:%M:%S %p\n%A, %B %d, %Y")
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

            draw.rectangle(expires_bbox, fill="white")
            remaining_seconds = 3600 - i
            minutes, seconds = divmod(remaining_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            expires_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
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

            if i % 2 != 0:
                draw.rectangle(bar_bbox, fill="white")

            frames.append(np.array(frame))

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            out_path = tmp_file.name

        logging.debug(f"Starting video write to {out_path}")
        clip = ImageSequenceClip(frames, fps=1)
        clip.write_videofile(out_path, codec="libx264", audio=False, verbose=True, logger='bar')
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