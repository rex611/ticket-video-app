from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import datetime
import os
import tempfile
from moviepy.editor import ImageSequenceClip

app = Flask(__name__)

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
        file = request.files['file']
        img = Image.open(file.stream).convert("RGB")

        w, h = img.size  # Ensures video shape = image shape (width x height)
        frames = []
        base_time = datetime.datetime.now()

        # Load Roboto SemiBold font with larger size
        try:
            font = ImageFont.truetype("Roboto-SemiBold.ttf", 33.5)  # Larger size, adjust as needed
        except IOError:
            font = ImageFont.load_default().font_variant(size=33.5)  # Fallback with large size

        # Positions based on your provided coordinates
        timestamp_pos = (w // 2 - 200, h - 350)
        timestamp_bbox = [w // 2 - 250, h - 400, w // 2 + 250, h - 260]
        expires_pos = (w // 2 - 150, h - 200)
        expires_bbox = [w // 2 - 200, h - 205, w // 2 + 200, h - 150]
        bar_bbox = [0, h - 260, w, h - 205]  # 3-way bar area (blinks by hiding/showing original)

        for i in range(60):
            frame = img.copy()
            draw = ImageDraw.Draw(frame)

            # Erase and update timestamp (moves like a clock)
            draw.rectangle(timestamp_bbox, fill="white")
            current_time = base_time + datetime.timedelta(seconds=i)
            timestamp_text = current_time.strftime("%I:%M:%S %p\n%A, %B %d, %Y")
            timestamp_lines = timestamp_text.split('\n')
            y_offset = timestamp_pos[1]  # Start at top-left y
            for idx, line in enumerate(timestamp_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                x = w // 2 - line_width // 2  # True center of the image, ignoring initial offset
                if idx == 0:
                    draw.text((x, y_offset), line, fill="black", font=font)
                else:
                    # Add extra spacing for the second line (date)
                    extra_spacing = 6  # Adjust this value to move the lower line down (e.g., 20px)
                    draw.text((x, y_offset + (idx * (bbox[3] - bbox[1])) + extra_spacing), line, fill="black", font=font)

            # Erase and update expires (fixed for now)
            draw.rectangle(expires_bbox, fill="white")
            expires_text = "Expires in 00:00:59"
            expires_lines = expires_text.split('\n')
            y_offset = expires_pos[1]
            for idx, line in enumerate(expires_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                x = w // 2 - line_width // 2  # True center of the image
                if idx == 0:
                    draw.text((x, y_offset), line, fill="black", font=font)
                else:
                    extra_spacing = 20  # Adjust this value to move the lower line down
                    draw.text((x, y_offset + (idx * (bbox[3] - bbox[1])) + extra_spacing), line, fill="black", font=font)

            # Blink bar: hide on odd seconds
            if i % 2 != 0:
                draw.rectangle(bar_bbox, fill="white")

            frames.append(np.array(frame))

        # Use tempfile for output
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            out_path = tmp_file.name

        # Write video with verbose logging
        clip = ImageSequenceClip(frames, fps=1)
        clip.write_videofile(out_path, codec="libx264", audio=False, verbose=True, logger='bar')

        # Send file and clean up
        response = send_file(out_path, mimetype="video/mp4")
        @response.call_on_close
        def cleanup():
            try:
                os.remove(out_path)
            except OSError:
                pass

        return response

    except Exception as e:
        return f"Error generating video: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)