"""Draw original catalogue illustrations; no external image or network dependency."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parents[1]/'frontend/public/assets'
OUT.mkdir(parents=True,exist_ok=True)
FONT=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',24)


def make(name):
    im=Image.new('RGB',(480,400),'#fbfbfc')
    d=ImageDraw.Draw(im)
    d.ellipse((80,330,405,362),fill='#e6e8ed')
    if name in ['pen-blue','pen-box']:
        count=3 if name=='pen-box' else 1
        for i in range(count):
            x=175+i*42
            d.rounded_rectangle((x,65,x+27,295),radius=9,fill='#2965b6',outline='#174b91',width=3)
            d.rectangle((x+7,76,x+14,245),fill='#7299d0')
            d.polygon([(x+2,295),(x+25,295),(x+13,338)],fill='#b1becb')
            d.line((x+13,326,x+13,343),fill='#18364c',width=3)
            d.rounded_rectangle((x+20,87,x+37,165),radius=5,outline='#193e70',width=5)
    elif name in ['notebook','exercise']:
        d.rounded_rectangle((120,52,350,334),radius=8,fill='#adb6d9' if name=='notebook' else '#a8cfc7')
        d.rectangle((140,55,148,331),fill='#7884b0')
        d.rectangle((180,140,302,212),fill='#f4f3ec')
        d.text((198,158),'NOTES',font=FONT,fill='#596274')
        for y in range(65,320,24):
            d.ellipse((109,y,132,y+11),outline='#5c6576',width=3)
        for y in range(244,300,12):
            d.line((180,y,304,y),fill='#d2dbeb',width=2)
    elif name=='paper':
        for i in range(8):
            d.rectangle((105+i,84-i*2,372+i,324-i*2),fill='#ffffff',outline='#c9cfd7',width=2)
        d.rectangle((113,68,380,285),fill='#7eb69a')
        d.rectangle((126,81,367,272),outline='#e1eee6',width=3)
        d.text((176,122),'Double A',font=FONT,fill='#fff')
        d.text((193,176),'A4 80',font=FONT,fill='#174e3c')
        d.text((171,218),'500 sheets',font=FONT,fill='#fff')
    elif name=='ruler':
        d.polygon([(110,90),(361,315),(110,315)],fill='#9ccdd7',outline='#498c9c',width=4)
        d.polygon([(150,179),(252,275),(150,275)],fill='#fbfbfc',outline='#498c9c')
        for x in range(118,355,15):
            d.line((x,295,x,312),fill='#327789',width=2)
    elif name=='folder':
        d.polygon([(120,90),(333,61),(368,321),(154,350)],fill='#33889b')
        d.polygon([(120,90),(153,86),(188,345),(154,350)],fill='#216579')
        d.polygon([(189,125),(300,111),(315,218),(203,232)],fill='#f4f4ee')
        d.ellipse((151,281,175,306),fill='#e1e9e8',outline='#183f54',width=4)
    elif name in ['colors','paint']:
        d.rounded_rectangle((92,99,386,316),radius=9,fill='#f1c77e')
        colors=['#bd4b64','#eea351','#dfcd67','#84ac78','#67aeb5','#6276a6','#a184b2','#d891aa']
        for i,color in enumerate(colors):
            x=111+i*32
            if name=='colors':
                d.rectangle((x,126,x+18,279),fill=color)
                d.polygon([(x,126),(x+18,126),(x+9,103)],fill='#e4c79e')
            else:
                d.ellipse((x,155,x+24,191),fill=color,outline='#fff',width=3)
        d.text((152,283),'COLOKIT',font=FONT,fill='#8e6639')
    elif name=='scissors':
        d.line((189,244,296,78),fill='#9faebf',width=17)
        d.line((271,244,174,77),fill='#b9c5ce',width=17)
        d.ellipse((117,228,219,332),outline='#d28ba5',width=22)
        d.ellipse((249,228,351,332),outline='#d28ba5',width=22)
        d.ellipse((220,172,244,196),fill='#6b7685')
    elif name=='tape':
        d.ellipse((111,109,370,309),fill='#ce9bb1')
        d.ellipse((127,95,357,246),fill='#efc9d9',outline='#c391a8',width=3)
        d.ellipse((175,126,309,213),fill='#fbfbfc',outline='#a17a8d',width=10)
        for x in range(130,350,27):
            d.line((x,250,x+10,286),fill='#e8bed0',width=4)
    else:
        d.rounded_rectangle((107,100,368,320),radius=14,fill='#d8e5df',outline='#adc9bd',width=3)
        for i,c in enumerate(['#be7894','#6f9fb7','#c6a568','#8b9e82']):
            x=143+i*48
            d.rounded_rectangle((x,143,x+35,265),radius=14,outline=c,width=8)
            d.rounded_rectangle((x+9,157,x+25,252),radius=8,outline=c,width=3)
    im.save(OUT/f'{name}.png',optimize=True)


if __name__=='__main__':
    for name in ['pen-blue','pen-box','notebook','exercise','paper','ruler','folder','colors','paint','scissors','tape','clips']:
        make(name)
