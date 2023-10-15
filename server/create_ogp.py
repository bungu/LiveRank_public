from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import os

def add_text_to_image(img, text, font_path, font_size, font_color, height, width, max_length=740):
    position = (width, height)
    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(img)
    if draw.textsize(text, font=font)[0] > max_length:
        while draw.textsize(text + '…', font=font)[0] > max_length:
            text = text[:-1]
        text = text + '…'

    draw.text(position, text, font_color, font=font)

    return img

def create_ogp_image(file_name,icon_name,japanese,english,comment):
    base = os.path.dirname(os.path.abspath(__file__))
    file_name=os.path.join(base,"../your_tw/static/",file_name)
    
    if os.path.isfile(file_name):
        return
    
    # filenameに ogp/が入っている
    icon_path=os.path.join(base, "../your_tw/static",icon_name)
    background_path=os.path.join(base, "../your_tw/static/img/background.png")
    canvas = Image.open(background_path).copy()
    w,h= canvas.size

    icon=Image.open(icon_path).copy()
    icon = icon.resize(size=(230, 230), resample=Image.ANTIALIAS)
    icon_w,icon_h=icon.size
    canvas.paste(icon, (w//2-icon_w//2,h//2-icon_h//2+75), icon)

    title_font_path=os.path.join(base, "../your_tw/static/font/Oswald-VariableFont_wght.ttf")
    title_font_size=32

    japanese_font_path=os.path.join(base, "../your_tw/static/font/ZenAntiqueSoft-Regular.ttf")
    japanese_font_size=64*0.6

    english_font_path=os.path.join(base, "../your_tw/static/font/Oswald-VariableFont_wght.ttf")
    english_font_size=32

    comment_font_path=os.path.join(base, "../your_tw/static/font/ShipporiMincho-Regular.ttf")
    comment_font_size=22.4

    text="Your Type Is"
    font_path=title_font_path
    fontsize=int(title_font_size*1.25)
    width=w//2-len(text)*fontsize*0.15
    canvas = add_text_to_image(img=canvas,
                    text=text, 
                    font_path=font_path,
                    font_size=fontsize, 
                    font_color=(0,0,0), 
                    height=h//2-230,
                    width=width
                    )

    text=japanese
    font_path=japanese_font_path
    fontsize=int(japanese_font_size*1.25)
    width=w//2-len(text)*fontsize*0.5
    canvas = add_text_to_image(img=canvas,
                    text=text, 
                    font_path=font_path,
                    font_size=fontsize, 
                    font_color=(0,0,0), 
                    height=h//2-180,
                    width=width
                    )

    text=english
    font_path=english_font_path
    fontsize=int(english_font_size*1.25)
    width=w//2-len(text)*fontsize*0.15
    canvas = add_text_to_image(img=canvas,
                    text=text, 
                    font_path=font_path,
                    font_size=fontsize, 
                    font_color=(0,0,0), 
                    height=h//2-125,
                    width=width
                    )

    text=comment
    font_path=comment_font_path
    fontsize=int(comment_font_size*1.25)
    width=w//2-len(text)*fontsize*0.5
    canvas = add_text_to_image(img=canvas,
                    text=text, 
                    font_path=font_path,
                    font_size=fontsize, 
                    font_color=(0,0,0), 
                    height=h//2+190,
                    width=width
                    )

    canvas.save(file_name)