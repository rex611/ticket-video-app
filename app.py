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

        # Load font (fallback if DejaVuSans missing)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 30)  # Adjust path if needed; or download font to your dir
        except IOError:
            font = ImageFont.load_default()

        # Positions based on your screenshot (adjust if needed for precision)
        timestamp_pos = (w // 2 - 200, h - 300)
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
            draw.text(timestamp_pos, timestamp_text, fill="black", font=font)

            # Erase and update expires (fixed for now; uncomment to countdown from ~1 min)
            draw.rectangle(expires_bbox, fill="white")
            expires_text = "Expires in 00:59:59"
            # remaining_secs = 3599 - i  # Example: countdown from 59:59
            # mins, secs = divmod(remaining_secs, 60)
            # expires_text = f"Expires in 00:{mins:02d}:{secs:02d}"
            draw.text(expires_pos, expires_text, fill="black", font=font)

            # Blink bar: hide on odd seconds (white over it), show original on even (keeps same colors)
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