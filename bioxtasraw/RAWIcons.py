'''Created on Fri Mar  4 16:24:49 2016

@author: Jesse B. Hopkins

This module contains embedded image data for all of the image
files in the resources directory. It was generated using the
wx.tools.img2py.img2py function, and automated with the
EmbeddedRAWIcons.py file.

It had the additional raw_icon_embed added to it by hand, which used to be in the RAW.py file.

#******************************************************************************
# This file is part of RAW.
#
#    RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************
'''
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map
from io import open

from wx.lib.embeddedimage import PyEmbeddedImage

checked = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAApFJ"
    "REFUOI2Vk11ojXEcxz////M4789zXnZYltisGYuLkXHHxRC7EFlJeYlaxLgWu2MtIVco7qQo"
    "xMXKaiklxbRa5CXHGiLm5bAXzzlnz/P/uThzxqX/1b++v9+3z6++X/jPV1NTI4B0dXXJ/+7S"
    "0dEhgDQ2NlaWFcDylt0y+OQLSBTEBmVA1F8jAtZPCPpQSiFSEbE3t5+RObWr6TnfQNoJA2AA"
    "RNBKYRAQOLBzE4MD0NDUSjTeLEOPTykA+85dw65uh2efPcL5IiJgaU1gAoyUCZ7cu8ngwEMS"
    "yTRr9p/g0rEHlbNsa2E1qUSEcc9nvGAhEqCVhZqGLHq/uHO5G4A17Z2k0hmsutkEQ2Vd60SU"
    "yZLhUf8NTu9bwak9zXz6MMxECUpG0Xelh5/fRplbt4RlrXspBgodj1YItOXE+OFp6lq2EHWr"
    "+DUxxu1zRzAo3r95yUD/NbBDrO84zUQBPuTNPwa2joZ5lxe+jGlqt5xl9EI7H4efcuvyGfK5"
    "++CXmLdyG2+lkeDtFJMFg+VEZgjC8QiO4+JmUlQvWkXTuoMAvOm/yPeRIWLJLEvbu3GcBOmq"
    "FMlMknA8NkMQdxzcdJZERKO1sHxHD19f3WM0NwhA8/YeqmsbCHwDolFhj4SbIP/HwHHjpNM2"
    "TgS0VY7NxqNXud65kqr5TbRs3YcJQGvNlA+hRBTHTc0QhCIOyRQkXbABHYJkdjGth06yYMVa"
    "snPB98th1ArGihCO/WUwyxuhet4cMlkIWRAIWArmHz+MCPgFsMIgBvwS2AVQ4y9mDJzxB4y8"
    "zrO4YQOzAD2dfjP9993pQaAIDPX2kZl8XjFQAG1tbZLL5fA8D2NMWSiXBpFy8SzLIhaLUV9f"
    "T29vb6VMvwFEculj1FOOfgAAAABJRU5ErkJggg==")

notchecked = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAWtJ"
    "REFUOI2tkjGO8jAQhd/YAzhOhOg4QFpuwi04SK7BFegRJaLgGhRI0NBBE4ckY/+VHYX9tVvs"
    "juTCzzPfvLEN/DIIADabTXi9XsiyDMwMAAghjBJFBHVdY7lcYrvd0uhwt9sF51zouu7b5ZwL"
    "+/0+VFWV6FxVVVitVni/32jbFkT0XwdRK8sS5/M5afx8PqG1Rtd1384agUQEa+0AWCwW8N6j"
    "7/uU8FmotYb3PkFEZADM53N475NIRCCi0Qje+1TYNA2KohgAWmvUdZ2SlFLpUESgtYaIJGdN"
    "08AYMwCKooAxBtPp9AuAiCAi6WmVUqM9ALC1Fnmeg5kRQkgjxIgOIrDv+7EDZoYxBsw8IsdL"
    "nUwmaNsWzAwRQZ7nXwGz2QzWWoQQoJRK9xG7fhSM9/f7HXmeI8sy/BSxwePxSJq6Xq84nU4/"
    "Fkc3x+MRt9tt0ABgvV6Hy+UC51yy//kXlFKw1qIsSxwOB8JfxT/2K8+JblgMHAAAAABJRU5E"
    "rkJggg==")

raw = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAABHNCSVQICAgIfAhkiAAABP5J"
    "REFUaIHtl99Pk2cUxz/Wgh0U6K8hv1qKrRUUS6d1kgX0ApjJNIZozC63C67c1S6X7WZXZtM/"
    "YDEm2y62BZbpxXajFidlUcyAtR1EKTQtLVhW21LagtWi7IL2pa8SR0K27k38Jm/65jzPOc/3"
    "+5zznOftjjdO315DwpCXKUuKzWFbkFeUS1xAZYXEBaiV8mJz2BbkaqmfAY3US0hXKfES0km9"
    "hN6UeglVV0pcwG6pC6iRuIAd2ZU1SX/M7Vhbk7YAWbEJbBeSF7DpNXzXeZtdfp/Iptbq/hNC"
    "W0FS30hbmw3Y5Azcdd7m/uUrHJzw8LxGi2whxvMabVGIvog96SQArt0GZOc/oqur+2UBbrcL"
    "n8u15aBlCsVLtpVM5pVzXxwvjJEfK1MoWMlkRD6Jmw4OTngwKkv42dhC14UL4hKaDYUIjtzF"
    "tJzaEvlnWi1Pamto7zwu2H65/BW1D4ObO1gPU/f2UcZuDWKKRdaJLS1C1wnaO4/j8bh55hpj"
    "Zyy2IahxD+1nzhKcm8M75MCY+3bTP15m7NagWMCMd4rqawPU5VKVRyCdFRxfxMzHnwjv1wf6"
    "qb42gGwhtunc5/dGSJjNVDU0kPnhW2QLMczKElyhEMEmEwzeQH+1X+Tj2m3AYzbD4A1U4x7I"
    "8QjW1dPZ0b4hYDYUYv7OHVoWYsKkQDqLp/MYarudELA4Okrr9KRAMGEyUW02AzAyPMTOgX4R"
    "+T9bregfL6PyrTcE2UKMlav9mPvO49h7AOuCk0A6i2rcg+PLL2idnhQ2K5DOAqBK+xi7eIkD"
    "0XlkOU4Jkwljby8WU/NGG33o91H6+z2BeCCdJXHIitpup1apFGqxkKCytRmrtQ2Px83spYsC"
    "0Tx5VU83wbp6AKKZVaKZVWT3Rnjo92Hs7SVhMhHNrAJgHXYKsQc1NXg6jwmxDk54ROuGbW9h"
    "tuwDCtro9JATRWRJCKhTyAk3WciOjqIfdpJUVFKXiBPNjfkMelrOvE9wbo6xi5eo9fqJFqRe"
    "ORNgdeYKFTnyecQDfxG+fIWOzz9juK6eivlHkIgL4ymVhtKz52ix2bg/66fK66cQYfshDp8+"
    "TaNevyHA7XaxOuWloiBQwmRCaTCAwYAHKJ/1Cwv5FZU8PXIUlUbL0Ddfo5wJCH5LliZWKtWi"
    "RdMYKUsuCmRqR8eZcvyKva+P+7OfigUcsWG32bBa2wiePEUq8p3AK6XSoOrpRqXZaOtyAJ/L"
    "JSIB6+XR88GHAHg72pn4bYSln36kyuunIhFH7fqDGe87KA0GEmYjaYysqVUYe3sxW/bx5Omy"
    "KN7I9wOEC4TJI4/Yp1RQevYc4ZsOwV7f0YHV2gaA9b1TOCYmKeyJdptN2H0AudvtYnF0lPLq"
    "KpaqqwBYqVSj6johTLKYmtlVWs5QMMiDB9M0y+SsTk6hcg6S3d8GPd3Aeu/W6XQk4i93ob37"
    "9xM2GES22PwCVQ0Ngj9AiU7HyPCQSFDhvVG4+wBylUaLva+PaDSKTqcTfvNXdR6Nej1KgwGF"
    "ppoH8fUeXn99GK4PC3OSuWerCG1ii+WezZA6YuNJR7tYQKNeL0rJq1DbZGT65Lvk92Dz+/bf"
    "Q73FgsXULLK9/j9QbLwWUGzII8lssTlsC/JIcvWfZ/2PIY+kJJ6BR1IvoWhK4iUUk3oJSV5A"
    "fPlZsTlsC/JFqWcgkZb4IV5KSzwDSalnYHlZ4gJWJF5CfwMAO/nZo8ePdQAAAABJRU5ErkJg"
    "gg==")

logo_atom = PyEmbeddedImage(
    "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")

