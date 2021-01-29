from datetime import datetime


def split_cmodes(modes, targets, TYPE_AB, TYPE_C, TYPE_D):
    out = []
    sign = None
    targets = list(targets)
    for c in modes:
        if c in "+-":
            sign = c
        elif c in TYPE_AB or (c in TYPE_C and sign == "+"):
            out.append([sign, c, targets.pop(0)])
        elif c in TYPE_D:
            out.append([sign, c, ''])

    return out


def split_umodes(modes):
    out = []
    sign = None
    for c in modes:
        if c in '+-':
            sign = c
        else:
            out.append([sign, c])

    return out


def timestamp_now():
    return int(datetime.now().timestamp())


def ischannel(arg, chantypes):
    return arg[0] in chantypes


async def send(network, msg):
    await network._driver.wsendq.send(msg)

