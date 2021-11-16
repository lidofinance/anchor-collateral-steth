color_hl = '\x1b[38;5;141m'
color_green = '\033[92m'
color_yellow = '\033[93m'
color_gray = '\x1b[0;m'
color_end = '\033[0m'


def highlight(text, color = color_hl):
    return f'{color}{text}{color_end}'


def ok(text, value = None):
    result = highlight('[ok] ', color_green) + text

    if value is not None:
        result += ': ' + highlight(value, color_hl)

    print(result)

def nb(text, value = None):
    result = highlight('>>> ', color_yellow) + text

    if value is not None:
        result += ': ' + highlight(value, color_hl)

    print(result)
