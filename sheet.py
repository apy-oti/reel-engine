import sys, subprocess
from PIL import Image
page, ts = sys.argv[1], sys.argv[2]
subprocess.run(["python3", "render.py", page, "st", ts], check=True)
ims = [Image.open(f"st_{t}.jpg").resize((270, 480)) for t in ts.split(",")]
c = Image.new("RGB", (270 * min(4, len(ims)), 480 * ((len(ims) + 3) // 4)))
for i, im in enumerate(ims): c.paste(im, ((i % 4) * 270, (i // 4) * 480))
c.save("contact.jpg")
