import argparse
import os

import OCR
import Linguist


def main():
    parser = argparse.ArgumentParser()

    # Required:
    requiredNamed = parser.add_argument_group('required named arguments')

    requiredNamed.add_argument('-t', '--tess_path',
                           help="path to the cmd root of tesseract install",
                           metavar='', required=False, default='C:\\Program Files\\Tesseract-OCR\\tesseract.exe')


    # Optional:
    parser.add_argument('-c', '--crop', nargs=2, type=int, metavar='', default=[100, 100])


    parser.add_argument('-v', '--view_mode', default=1, type=int, metavar='')
    parser.add_argument('-sv', '--show_views', action="store_true")

    parser.add_argument("-l", "--language", metavar='', default=None)
    parser.add_argument("-sl", "--show_langs", action="store_true")
    parser.add_argument("-s", "--src", default=0, type=int)

    args = parser.parse_args()

    if args.show_langs:
        Linguist.show_codes()

    if args.show_views:
        print(OCR.views.__doc__)

    tess_path = os.path.normpath(args.tess_path)
    # This is where OCR is started...
    OCR.tesseract_location(tess_path)
    OCR.ocr_stream(view_mode=args.view_mode, source=args.src, crop=args.crop, language=args.language)


if __name__ == '__main__':
    main()
