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


def morefmt(number):
    #s = f" \x02({number} more message{{}})".format("s" if number != 1 else "")
    s = f" \x02({number} more)"
    return s

def andify(L):
    if not L:
        return ""
    elif len(L) == 1:
        return L[0]
    elif len(L) == 2:
        return " and ".join(L)
    else:
        return ", ".join(L[:-1]) + f", and {L[-1]}"


async def send(network, msg):
    await network._driver.wsendq.send(msg)
