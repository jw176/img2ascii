import shutil
from collections import namedtuple
import itertools
import time
import argparse

import numpy as np
from PIL import ImageFont, Image, ImageDraw, ImageEnhance
from colorama import Fore, init, Back, Style
from numba import njit



init()

Color = namedtuple('Color', ['name', 'fore', 'back'])
colours = [
    Color(name="black", fore=Fore.BLACK, back=Back.BLACK),
    Color(name="red", fore=Fore.RED, back=Back.RED),
    Color(name="green", fore=Fore.GREEN, back=Back.GREEN),
    Color(name="yellow", fore=Fore.YELLOW, back=Back.YELLOW),
    Color(name="blue", fore=Fore.BLUE, back=Back.BLUE),
    Color(name="magenta", fore=Fore.MAGENTA, back=Back.MAGENTA),
    Color(name="cyan", fore=Fore.CYAN, back=Back.CYAN),
    Color(name="white", fore=Fore.WHITE, back=Back.WHITE)
]


def get_font_bitmap(colours, ascii_start=32, ascii_stop=127):
    font = ImageFont.truetype(font='fonts/CascadiaMono.ttf', size=16)
    bitmaps = np.zeros((ascii_stop - ascii_start, len(colours), 16, 9, 3))
    for i in range(ascii_start, ascii_stop):
        for j, (fore, back) in enumerate(colours):
            chr_bitmap = get_char_bitmap(chr(i), font, fore, back)
            bitmaps[i - ascii_start, j] = chr_bitmap
    return bitmaps


def get_char_bitmap(char, font, fore_color, back_color):
    img = Image.new(mode='RGB', size=(9, 16), color=back_color.name)
    draw = ImageDraw.Draw(im=img)
    draw.text(xy=(5, 8), text=char, font=font, fill=fore_color.name, anchor='mm')
    return np.array(img)


def load_img(filename, x_gap=4, y_gap=10, chr_width=9, chr_height=16, target_width=None, target_height=None):
    img = Image.open(filename)
    img = img.convert(mode="RGB")

    brightness = ImageEnhance.Brightness(img)
    img = brightness.enhance(0.7)

    contrast = ImageEnhance.Contrast(img)
    img = contrast.enhance(1.5)
    # img.show()

    width, height = img.size

    if target_width:
        factor = target_width / width
        width = round(target_width)
        height = round(factor * height)

    if target_height:
        factor = target_height / height
        height = round(target_height)
        width = round(factor * width)

    new_width = (width // (x_gap + chr_width)) * (x_gap + chr_width)
    new_height = (height // (y_gap + chr_height)) * (y_gap + chr_height)
    img = img.resize((new_width, new_height))
    return np.array(img)


@njit()
def get_ascii_representation(img, chr_bitmaps, x_gap=4, y_gap=10, chr_width=9, chr_height=16):
    ascii_img = []

    for y in range(0, img.shape[0], (y_gap + chr_height)):
        ascii_row = []
        for x in range(0, img.shape[1], (x_gap + chr_width)):
            min_value = np.inf
            min_index = (0, 0)
            for index, character_bitmaps in enumerate(chr_bitmaps):
                for c_index, coloured_bitmap in enumerate(character_bitmaps):
                    # val = np.abs(img[])
                    img_section = img[y:(y + chr_height), x:(x + chr_width)]
                    val = np.sum(np.abs(img_section - coloured_bitmap))

                    if val < min_value:
                        min_value = val
                        min_index = (index, c_index)

            ascii_row.append(min_index)
        ascii_img.append(ascii_row)
    return ascii_img


def get_string_representation(index_data, ascii_start, colour_combinations):
    str_img = []
    for row in index_data:
        str_row = []
        for ascii_index, c_index in row:
            fore, back = colour_combinations[c_index]
            character = chr(ascii_index + ascii_start)
            if fore.name != "white":
                character = fore.fore + character + Fore.RESET
            if back.name != "black":
                character = back.back + character + Back.RESET
            str_row.append(character)
        str_img.append(str_row)
    return str_img


def main(ascii_start, ascii_stop, x_gap, y_gap, chr_width, chr_height, input_img, width=None, height=None,
         output_file=None, to_print=True, coloured_foreground=False, light_background=False, coloured_background=False):

    colour_combinations = list(itertools.combinations(colours, 2)) + list(itertools.combinations(colours[::-1], 2))
    colour_combinations = list(set(colour_combinations))

    if light_background:
        colour_combinations = list(filter(lambda x: x[1].name == "white", colour_combinations))
    elif not coloured_background:
        colour_combinations = list(filter(lambda x: x[1].name == "black", colour_combinations))

    if not coloured_foreground:
        text_colour = "white" if not light_background else "black"
        colour_combinations = list(filter(lambda x: x[0].name == text_colour, colour_combinations))

    chr_bitmaps = get_font_bitmap(colour_combinations, ascii_start=ascii_start, ascii_stop=ascii_stop)

    target_height, target_width = None, None
    if width is None and height is None:
        terminal_size = shutil.get_terminal_size((80, 20))
        target_height = (terminal_size.lines - 1) * (y_gap + chr_height)
    else:
        target_width = width
        target_height = height

    img = load_img(input_img, x_gap=x_gap, y_gap=y_gap, chr_width=chr_width, chr_height=chr_height,
                   target_width=target_width, target_height=target_height)

    ascii_img = get_ascii_representation(img, chr_bitmaps, x_gap=x_gap, y_gap=y_gap, chr_width=chr_width,
                                         chr_height=chr_height)

    str_img = get_string_representation(ascii_img, ascii_start, colour_combinations)

    if to_print:
        print("\n".join("".join(row) for row in str_img))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert an image into ascii art.")
    parser.add_argument('source', type=str, help="the filename of the image to convert to ascii")
    parser.add_argument('--ascii-start', '--start', type=int, default=32,
                        help="The starting value of the ascii characters")
    parser.add_argument('--ascii-stop', '--stop', type=int, default=126, help="The end value of the ascii characters")
    parser.add_argument('--output', '-o', type=str, default=32, help="Optional output file to save as image")

    parser.add_argument('--coloured-foreground', '-cf', dest='coloured_foreground', action='store_true',
                        help="Use coloured printing to the terminal")

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--colour-background', '-cb', dest='coloured_background', action='store_true',
                       help="Use coloured background when printing")
    group.add_argument('--light-background', '-lb', dest='light_background', action='store_true',
                       help="Use a light background when printing")
    group.add_argument('--dark-background', '-db', dest='dark_background', action='store_true',
                       help="Use a dark background when printing")

    x_gap = 4
    y_gap = 10
    chr_width = 9
    chr_height = 16

    args = parser.parse_args()
    print(args)

    main(args.ascii_start, args.ascii_stop, x_gap, y_gap, chr_width, chr_height, args.source,
         coloured_foreground=args.coloured_foreground, light_background=args.light_background,
         coloured_background=args.coloured_background)
