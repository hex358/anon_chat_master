from random import randint

def gen(length):
    numbers = list("0123456789")
    output = ''
    for i in range(length):
        output += numbers[randint(0,9)]

    return output


def id_gen(length):
    numbers = list("0123456789")
    output = ''
    for i in range(length):
        output += numbers[randint(0,9)]

    return int(output)

def gen_split(length):
    letters_low = list("abcdefghijklmnopqrstuvwxyz")
    letters_caps = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    numbers = list("0123456789")
    output = ''
    tick = 0
    for i in range(length):
        tick = randint(1,4)
        if tick == 1: output += letters_low[randint(0,24)]
        elif tick == 2: output += letters_caps[randint(0,24)]
        else: output += numbers[randint(0,9)]

    return output

def gen_alt(length):
    numbers = list("0123456789")
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    output = 'u'
    for i in range((length * 2) // 3):
        output += numbers[randint(0,9)]
    for i in range(length // 3):
        output += letters[randint(0,24)]

    return output