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
    file = request.files['file']
    img = Image.open(file.stream).convert("RGB")

    w, h = img.size  # Correct: w = width, h = height
    frames = []
    base_time = datetime.datetime.now()

    # Load a system font for larger text (adjust path if needed; DejaVuSans is common on Linux)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except IOError:
        font = ImageFont.load_default()  # Fallback to small default if font missing

    # Approximate positions based on screenshot layout (adjust as needed)
    timestamp_pos = (w // 2 - 200, h - 250)  # Centered near bottom
    timestamp_bbox = [w // 2 - 250, h - 260, w // 2 + 250, h - 200]  # Area to erase old timestamp
    expires_pos = (w // 2 - 150, h - 180)  # Below timestamp
    expires_bbox = [w // 2 - 200, h - 190, w // 2 + 200, h - 150]  # Area to erase old expires
    bar_bbox = [50, h - 140, w - 50, h - 120]  # Horizontal bar area near bottom (adjust for exact)

    for i in range(60):  # 60 frames for 60 seconds
        frame = img.copy()
        draw = ImageDraw.Draw(frame)

        # Erase old timestamp area
        draw.rectangle(timestamp_bbox, fill="white")

        # Draw updated timestamp (ticking forward)
        current_time = base_time + datetime.timedelta(seconds=i)
        timestamp_text = current_time.strftime("%I:%M:%S %p\n%A, %B %d, %Y")
        draw.text(timestamp_pos, timestamp_text, fill="black", font=font)

        # Erase old expires area
        draw.rectangle(expires_bbox, fill="white")

        # Draw updated expires text (fixed for now; uncomment below to count down)
        expires_text = "Expires in 00:59:59"  # Example fixed value; adjust format
        # To count down (e.g., from 60 minutes):
        # remaining_secs = 3600 - i  # Start from 1 hour
        # mins, secs = divmod(remaining_secs, 60)
        # expires_text = f"Expires in 00:{mins:02d}:{secs:02d}"
        draw.text(expires_pos, expires_text, fill="black", font=font)

        # Blink the bar: hide on odd seconds by drawing white over it
        if i % 2 != 0:
            draw.rectangle(bar_bbox, fill="white")

        frames.append(np.array(frame))

    # Use tempfile for output to auto-clean
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
        out_path = tmp_file.name

    # Write video with moviepy (fps=1 for 60-sec video)
    clip = ImageSequenceClip(frames, fps=1)
    clip.write_videofile(out_path, codec="libx264", audio=False)

    # Send file and clean up after
    response = send_file(out_path, mimetype="video/mp4")
    @response.call_on_close
    def cleanup():
        try:
            os.remove(out_path)
        except OSError:
            pass

    return response