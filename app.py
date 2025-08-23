from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np, datetime, os

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

    h, w = img.size
    frames = []
    font = ImageFont.load_default()

    for i in range(60):  # 60 seconds video
        frame = img.copy()
        draw = ImageDraw.Draw(frame)

        # Add current timestamp
        now = datetime.datetime.now().strftime("%I:%M:%S %p\n%A, %b %d, %Y")
        draw.text((w//2-150, h-200), now, fill="black", font=font)

        # Blink bar (visible on even seconds)
        if i % 2 == 0:
            draw.rectangle([50, h-80, w-50, h-60], fill=(0, 0, 255))

        frames.append(np.array(frame))

    out_path = "output.mp4"
    out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), 1, (img.width, img.height))
    for f in frames:
        out.write(cv2.cvtColor(f, cv2.COLOR_RGB2BGR))
    out.release()

    return send_file(out_path, mimetype="video/mp4")
