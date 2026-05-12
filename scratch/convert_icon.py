from PIL import Image
import os

img = Image.open("auhip_icon.png")
icon_size = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("auhip_icon.ico", sizes=icon_size)
print("Converted auhip_icon.png to auhip_icon.ico")
