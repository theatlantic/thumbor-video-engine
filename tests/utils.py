# -*- coding: utf-8 -*-
import math


def esc_code(codes=None):
    if codes is None:
        # reset escape code
        return "\x1b[0m"
    if not isinstance(codes, (list, tuple)):
        codes = [codes]
    return "\x1b[0;" + ";".join(map(str, codes)) + "m"


def get_luminance(rgb):
    rgb_map = []
    for val in rgb:
        val = val / 256
        if val <= 0.03928:
            rgb_map.append(val / 12.92)
        else:
            rgb_map.append(pow((val + 0.055) / 1.055, 2.4))

    return (0.2126 * rgb_map[0]) + (0.7152 * rgb_map[1]) + (0.0722 * rgb_map[2])


def repr_rgb(rgb):
    r, g, b = rgb
    codes = (48, 2, r, g, b)
    reset = "\x1b[0m"
    hex_color = "#%s" % ("".join(["%02x" % c for c in rgb]))
    luminance = get_luminance(rgb)
    if luminance > 0.5:
        codes += (38, 2, 0, 0, 0)
    else:
        codes += (38, 2, 255, 255, 255)

    return "%(codes)s%(hex)s%(reset)s" % {
        "codes": esc_code(codes),
        "hex": hex_color,
        "reset": reset,
    }


def rgb_to_lab(input_color):
    RGB = [0, 0, 0]

    for i, value in enumerate(input_color):
        value = float(value) / 255

        if value > 0.04045:
            value = ((value + 0.055) / 1.055) ** 2.4
        else:
            value = value / 12.92

        RGB[i] = value * 100

    XYZ = [0, 0, 0]

    X = RGB[0] * 0.4124 + RGB[1] * 0.3576 + RGB[2] * 0.1805
    Y = RGB[0] * 0.2126 + RGB[1] * 0.7152 + RGB[2] * 0.0722
    Z = RGB[0] * 0.0193 + RGB[1] * 0.1192 + RGB[2] * 0.9504
    XYZ = [round(n, 4) for n in [X, Y, Z]]

    # Observer= 2°, Illuminant= D65
    XYZ[0] = float(XYZ[0]) / 95.047  # ref_X =  95.047
    XYZ[1] = float(XYZ[1]) / 100.0  # ref_Y = 100.000
    XYZ[2] = float(XYZ[2]) / 108.883  # ref_Z = 108.883

    for i, value in enumerate(XYZ):
        if value > 0.008856:
            value = value ** (0.3333333333333333)
        else:
            value = (7.787 * value) + (16 / 116)

        XYZ[i] = value

    Lab = [0, 0, 0]

    L = (116 * XYZ[1]) - 16
    a = 500 * (XYZ[0] - XYZ[1])
    b = 200 * (XYZ[1] - XYZ[2])

    Lab = [round(n, 4) for n in [L, a, b]]

    return Lab


def avg(*args):
    return float(sum(args)) / len(args)


def delta_e_cie2000(lab1, lab2, k_L=1.0, k_C=1.0, k_H=1.0):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    pow25_7 = math.pow(25, 7)
    C1 = math.sqrt(math.pow(a1, 2) + math.pow(b1, 2))
    C2 = math.sqrt(math.pow(a2, 2) + math.pow(b2, 2))
    C_avg = avg(C1, C2)
    G = 0.5 * (1 - math.sqrt(math.pow(C_avg, 7) / (math.pow(C_avg, 7) + pow25_7)))
    L1_ = L1
    a1_ = (1 + G) * a1
    b1_ = b1
    L2_ = L2
    a2_ = (1 + G) * a2
    b2_ = b2
    C1_ = math.sqrt(math.pow(a1_, 2) + math.pow(b1_, 2))
    C2_ = math.sqrt(math.pow(a2_, 2) + math.pow(b2_, 2))
    h1_ = (
        0
        if a1_ == 0 and b1_ == 0
        else math.degrees(math.atan2(b1_, a1_)) + (0 if b1_ >= 0 else 360.0)
    )
    h2_ = (
        0
        if a2_ == 0 and b2_ == 0
        else math.degrees(math.atan2(b2_, a2_)) + (0 if b2_ >= 0 else 360.0)
    )
    dh_cond = 1.0 if h2_ - h1_ > 180 else (2.0 if h2_ - h1_ < -180 else 0)
    dh_ = (
        h2_ - h1_
        if dh_cond == 0
        else (h2_ - h1_ - 360.0 if dh_cond == 1 else h2_ + 360.0 - h1_)
    )
    dL_ = L2_ - L1_
    dC_ = C2_ - C1_
    dH_ = 2 * math.sqrt(C1_ * C2_) * math.sin(math.radians(dh_ / 2.0))
    L__avg = avg(L1_, L2_)
    C__avg = avg(C1_, C2_)
    h__avg_cond = (
        3.0
        if C1_ * C2_ == 0
        else (0 if abs(h2_ - h1_) <= 180 else (1.0 if h2_ + h1_ < 360 else 2.0))
    )
    h__avg = (
        h1_ + h2_
        if h__avg_cond == 3
        else (
            avg(h1_, h2_)
            if h__avg_cond == 0
            else (avg(h1_, h2_) + 180.0 if h__avg_cond == 1 else avg(h1_, h2_) - 180.0)
        )
    )
    AB = math.pow(L__avg - 50.0, 2)  # (L'_ave-50)^2
    S_L = 1 + 0.015 * AB / math.sqrt(20.0 + AB)
    S_C = 1 + 0.045 * C__avg
    T = (
        1
        - 0.17 * math.cos(math.radians(h__avg - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h__avg))
        + 0.32 * math.cos(math.radians(3.0 * h__avg + 6.0))
        - 0.2 * math.cos(math.radians(4 * h__avg - 63.0))
    )
    S_H = 1 + 0.015 * C__avg * T
    dTheta = 30.0 * math.exp(-1 * math.pow((h__avg - 275.0) / 25.0, 2))
    R_C = 2.0 * math.sqrt(math.pow(C__avg, 7) / (math.pow(C__avg, 7) + pow25_7))
    R_T = -math.sin(math.radians(2.0 * dTheta)) * R_C
    AJ = dL_ / S_L / k_L  # dL' / k_L / S_L
    AK = dC_ / S_C / k_C  # dC' / k_C / S_C
    AL = dH_ / S_H / k_H  # dH' / k_H / S_H
    dE = math.sqrt(math.pow(AJ, 2) + math.pow(AK, 2) + math.pow(AL, 2) + R_T * AK * AL)

    dE_norm = dE / 100.0
    if dE_norm > 1:
        return 1
    elif dE_norm < 0:
        return 0
    else:
        return dE_norm


def color_diff(rgb_a, rgb_b):
    lab_a = rgb_to_lab(rgb_a)
    lab_b = rgb_to_lab(rgb_b)
    return delta_e_cie2000(lab_a, lab_b)
