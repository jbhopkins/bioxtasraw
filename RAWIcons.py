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
from wx.lib.embeddedimage import PyEmbeddedImage

center_arrow_up = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABGdBTUEAANkE3LLaAgAABNxJ"
    "REFUWMPFlk9sFFUcxz/zd3e2oRVYm7Vopaa2UNtC0xIxBINBPEhqFYsHEYMkhCAnwsGbIV4M"
    "IYaDCQcPeEEPiiExBAII8SDRxKSFtpGmBspibVkMLZTd7u7svHkeXiezu7TU2gZe8svMm9l9"
    "38/7vt/7vYEn3IyF/Pn92trtCceJ30ink4+dfMeqVe+M7d//V39n52+r4/EXH6v4J2vX7vMO"
    "Hy7IZFLKCxfkSFdXctOyZS8/FvEjbW2H5NGjUvb3SzkwIOX161JeuiTT27aNb4/Ht853vPnk"
    "gPl1S8uxj3fuPMiGDZDLQT4PU1NQVYXd2uq8nUp1304mR3sKhd7FBqg83dj47Xu7dn1AWxuk"
    "0+C64HlQKCiIaBSjo8PonJzs0q5dc3+W8pdFAXgOak7X1p56fc+eN2hogAcPlHihEIbnKUcA"
    "1q1jk+tufmpgYOk5OA/I/w1QD01nampOt+/d205NjRIPZj1T5HLq2t7O+khk/ere3lUn4QxQ"
    "mDfAq7DxVF3dj/W7d79AVZWyfTbhYifyeQXS3ExzdXXzut7eV37y/XMZyPxngDdh23cNDd8n"
    "urvjmCZkMuHMPS8MIUr7wXvXVXlRV0fDypV1r/X1bbnouhcnYHxOgI9g3/Hm5uNVW7Y4CAHZ"
    "bCgkRBi+X9ov/k0ANDUFiQQ1jY2JzUNDXZczmV9T8PesAAfh0JetrUciHR06+byaSSDk+w9H"
    "OcBsEMuXU11XV/VWT8+7PZ43cBP+LAewPte0Y5+1th7U6uvVGnrew4JSzt6fyRXPA02DiQk4"
    "f57K27edTugeknJ0EHoDgOgxwzhxoKnpQxIJJS6EGhxCkeC++HlxlDsjpRIfGYGzZ+HGDbAs"
    "YppmdEFXUsq7ffC7FoH6m/H4YKK62kBKsCwVtg2GAZEILF0Kpqmem6YKw1Ch62FomgpdV4l7"
    "6xYMD6tlgHC3CMHJdPrq9lxukynB6jEMd6UQjq7rGL6P4XnoUmJKyTPZLMaSJWqAQKA8AleC"
    "pL1zB0ZGuF8oMFZZiYzF8IXAEwIhBL4QDKrCZZkaFAZTqcJkKuUYQASwAQtwgKfXrMEoXnNZ"
    "VtiEUMmazcLkZFgpYzHGh4f54+pVfCA/Hbnp0nhTbUnXzMPoF3BgOTQVl00dvCWw7Acpd1W7"
    "rl2y9kFySVmadAAVFRCNAjBkGGOH4BupxtV8QANNgkjCOSBtAlOjcHwUzLKS4AFNrpQ7cF27"
    "xIHiXLBtBRO44ftqnaVkwrLG+uHT6cnrRWNLQECpqFdelGzwfNsGx1Gi0agStO0wEYPkC3ZC"
    "UBEBw7Ik6hzwp+OhZvLopmPbEIspAMdRu8K2QxeKAYQIy7GU+LZN2cznDYAMHAiuwX0AYRhh"
    "bgQArgtSIi1rruHnBigYRjjzWEzdR6OqHwBoWliAXFediIsFUGK946gsj8VUPxIpBQiOY8tS"
    "/UUBCCqeaYaijqMgolEloutKMKgHuq7ciEQWDiBWrICWFgUQLEGwDMFugND+XE5B+L56v0AA"
    "ze7ri1BRoayvrAwLjWEokWxW1f3JSbh/X5189+7B3btYV67MSfBIABfGv+rvv7wxlXpJOI4k"
    "Gp3Z9nxegWSz6uCZmoJMRp6ASzziexBAmwNQB54HnmWOr9sZxhWoD49/FgJQDDLfJucJ/WTa"
    "v3LkyYTQ/TcwAAAAAElFTkSuQmCC")

center_target = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAQAAADZc7J/AAACNklEQVRIx6WVQW6bQBSG/4ki"
    "yxYGxgukSo1E1RCUqgtbvYC5QXyD5Ab0BvgGpicgN7CPQC5QOYuqK1dedNHdkAu8P4tgYjDG"
    "VTLIi3l8/ue9/80winjfOAdUx+tvLrbAz9Fx4qxbXyaiRU+mnRl0CmgFgPrNGXAiEHBynFBs"
    "9eCrixlmiLBbu0COFVa/nv5L4EuMuWpJmwXmv3+cLOE6Y0otkEJSmQkEMpNUCgE10+usqdqY"
    "h1nIkKEJk3LOsETCJDQhQ4ZZh0AQBwwYmKtxFWFQIVfjwAQMGMRHPPjsYqs0CkSbx13sksCm"
    "Qi7HyKFZ4NOfpxYPOKMWSPr6d0Age8TmUVIBNWetJfhLn76pe+LTb9jkG5/+srULEhG8b5rc"
    "tJn3hES7WbmVL6bQmFATyOu4oDkkx3foiwRrFH8fFPHRxbbacYdjXv7aR3F+2MpmCd0Hvmzj"
    "hyk1Ji+rqVoRzAEV1SJRmdVaFf8eaqt7xqO3qK/g0Wsk6C08elWv6l3IBXLXNLFpo9wJJG8V"
    "4IqgHiV1D+oJjBJqgquaSdVLVxtNbfT4Naap9xA9fiFGbqsA4MQOHTrGqSQcOhXijB3j0KGz"
    "d5gOWmhnNm0OzbAsxKZdIsNkaGzatLuOMwBYmUWLFi1jLawbixatG2thmTJ66oMCAIN4YAZs"
    "ecwgPoDbd+HA7d/2l33TZ/mY/rJ/O3Bb0O6rrZf02GMvOU6culjWAID12wUKAEDRgXSXcOYq"
    "o0wXod57vT8DkKYDhZHJMwAAAAAASUVORK5CYII=")

CircleIcon = PyEmbeddedImage(
    "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")

close_eye = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAACK1BMVEUAAAD/AAD/AAC5RUWb"
    "m5yop6itra6VlZWAgIClUFH9AQH/AADLMTGhoaHgGxt7e3zExMWFNTbYHBx4eHl4eHmsrK6r"
    "q6xXV1jRLi7YCwyMjI5LS0x2dnd4eHl4eHl8fH1dXmDm6e3Y3OFGRkdwcXK9wcbO0tbP1Nlt"
    "bm1uc3a4vMHU2N65u792eHh4fHdZW1+WmZ7Y3eHc0dWpqax4eHlzc3dfa056eHVhZGFQVFjD"
    "YGL7GRnyCQmNXmB2enhxc3x7c3p7fHu7PDy9JSdqbHJucHVvcndqVVjsDQ6qSUmBYGvDbo6E"
    "Yob4BQbnFRV6eXl4eHp5d3l4eHp6d3d5dnbxDAzyCgt2bX59enrcAP+fjpBvbmfyCQl2dXR2"
    "eHZ2d3p3eHd3dnh4eXp4dHl5dnuAdX+AdHSWlWgADAcpWmtbY39uaXN4b3Z3dHJ2cn13cXl1"
    "dHV8dnaAd3dubm1QQb4BFwsbHVdTTnJvYohodnhqd3Z4b3Rzcm5wcHBlZGRGC/YFBQMfCRKH"
    "LllxYV5gbllmcmZXgHxXbaOhoaH/AAD+AgLfp6fMzMy0tLSHh4iKbW73BwfvNzdVVlhMTlE9"
    "MjblBgZ4eHmxTVBUWF7RCArz9PbRVVfhCAnhAAETCxLx8/To6+7z9fajp6p4HyT8AAD6AAAZ"
    "BQ0jKDDw8fTP09bU2d/R1djs7u+NGByvAQSVmJza3N/T1dfuh4h7DhP0AgP4LS7xjpDk5ejr"
    "ztFXf3kqAAAAiHRSTlMABTRPoNvr5Mme6Ckw+8Uf7v72eAzk2NPr/ovK2yR1loDphpBdXfid"
    "QDy9/IZNGGad7vSdhSsGKWSKxv70oVIdDCl30bi5uK/sSBMDCrq3Y3N/gn522sUeCAEBB3kg"
    "Lz5IT1JLOyYSBQICCA8YJCgqKyQYCwMBAgcKDxUWEw0GAQEDBgcKCgYDHp2ZugAAAP1JREFU"
    "GNNjYEACjFCaiZmFla2DnYOTixvM5+ns6u7p5e3rn9DJB+LzC0zs7BScNHnK1E6hacIMDCKi"
    "YuISnZ3TZ8zslJSSlpFlkJNXUJw1u7NzTufcefOVlIUZVFTVFixctLhzydJly1esVNdg0NRa"
    "tXrFmrWdnZ3r1m/Q1tFl0NM3MNy4qbNz85bOrUbGJqYMZuYWlladndu277DutLG1s2dgcHB0"
    "6ux0dnF1c/fo7PT0YmDw9vHt9PMPCAwKDgkNC49gYIiMio6JjYtPSExKTklNSwe5NSMzKzsn"
    "Ny+/oLCouATivdKy8orKquqa2rp6mM8bGpuaW1rb2hkAntVQmcFmROwAAAAASUVORK5CYII=")

collapse = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAPCAMAAADarb8dAAAAilBMVEX///8AAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAABbW1taWlpaWllZWVlYWFhcXFwAAAAAAABpaWlnZ2dpaWm1t7hrbGtz"
    "cnPBw8S6vL7Cw8V3d3jP0NKytLewsrV+f4DZ29yusLKtr7GNjpHg4eOnqa2nqayoqq1mZmbx"
    "8vXq6+3p6uxkZGRiYWFhYWEp0ym8AAAAEnRSTlMAAAQNFAMuPzLCwcHBwcAQBfC3O4Y5AAAA"
    "gUlEQVQI15XISRKCMBRF0WfyCUEJnYhIL42A4P63J0Qsq5h5ZvcCe4edz2CciLPfMEiYpiDj"
    "OwySVhBYUh/oPp7D8HLSB2vb0TWOb5G9HjCSKkmzPM/SREli4EIVZXVfVGWhBAc5ddN2j0XX"
    "NrVDcPthfG7GoXfh+dP82syT7+F/b2pFCxyRT88FAAAAAElFTkSuQmCC")

collapse_all = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAQlBMVEWQobeQobeUo7eVpbmd"
    "q7yXp7uhsMCZqb2ltMWbq7+qusudrcKvv9GrucvS3OfG0+C0xdesu8y5ydzY4u7P4vfk7/y0"
    "WrE9AAAAAXRSTlMAQObYZgAAAFpJREFUGNN1ztkOgCAMRNEOi4gIisv//6oEaiNRz+NN0wxR"
    "A1AHSnUF2hj9KLBDYaXAjZXjAj8xXwvCLEIpiGlZ2ZIiygDkjWW0OdgZZOWNfrwucDAJJ/t8"
    "egFPuwUDUT19JgAAAABJRU5ErkJggg==")

document = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAABv1BMVEUAAACRscOhu82cuMqW"
    "s8aUssWHq8J+pr8zbZNIfqE3dJpHfaEpaI8oZpElZY0kZI0hY4whYYwgYIseYIsfYIsdX4ss"
    "ZIsaWIBNf6A+dpk/dplBdJgLSXdhkaqivcv////29/rf6PDH19+xxtiFqsFMgp+buMn///zz"
    "+Pzl6/TX3+XG1uOWts2Jqry0yNaZtcj//fv9/f3y9/bg5+3d5O+mvtGauc2hu8+Wtcf9/fj7"
    "+/r6/fvr9/bp8fPK2eOTtMnc4+vG2eFznbeQscX9/fz5+fr9+/rw9/nk7vPF1N2rvtShvNCE"
    "p76Hp738/v34+/r8+vr++/r5+/zq8vXn7vDa4unU3ea0y9Z8nrH4/vzw+fn5+vv8+fr7/Pvd"
    "5erg5+zL2OZtlbDt9Pfs8fTt8vby8vn0+vr2/fv5+vzn7/Ts8fXi6vBmlrHv9Pbt8vXs8PTy"
    "8/nw+vv1+fvz9Pvz9/zj6u9nlrHv9vfu8fb09vzy8/r9+/7f6e9plrPu8/Xu8vXv8/f6/f3g"
    "6O9kka3v8vXt9fbo9PPq8PP5/Pzg6e9Whabs9PXo8fPn8PLe6O/g6e7i6+/t8/bi6/BSgKBE"
    "dZkoE5LeAAAAHXRSTlMA+/jz8/Pz88rR188N5OHh4eHh4eHh4fv48/Py1rRX0KYAAADcSURB"
    "VBjTY2BgYGRiZmFlY5flYIACOXl5BUUlZRVVTqiAmry6hqaWto6uHhdEQF/ewNDI2MTUTN6c"
    "mwckYCFvaWVtY2tn7+DoxAsScJZ3cXWzdvfw9PL24QMJ+Mr7+QcEBgWHhIaF84MEIuQjo6Jj"
    "YgNs4+ITBEACifJJySmpaekZmVnZgiCBHPncvOT8gsKi4pJSIZBAGVAgL6+8orKqukYYJFAL"
    "Fqirb8hrbBIBCTTL57YAQWtbe0cnWKBLvrvH1ra3r3/CxEmiIIHJ8gggBhIQl5CUggDpKTIM"
    "AP8XNkSA5NhCAAAAAElFTkSuQmCC")

errbars = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYBAMAAAASWSDLAAAAD1BMVEUAAACZmZn/////AAAA"
    "AP8VaDcuAAAAPElEQVQY02NgQAaMgnAgwMCoBAckcozgHCMoAnKUlYyU0TjKWDgqLlDghFcZ"
    "imko9qC5gEwvwDjIAYIMALFSID0ixfKDAAAAAElFTkSuQmCC")

expand = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAPCAMAAADarb8dAAAAilBMVEX///8AAAAAAABpaWkA"
    "AAAAAABcXFwAAAAAAABYWFgAAAAAAAAAAABZWVlaWllaWlpbW1sAAABkZGRiYWFhYWFmZmbx"
    "8vXq6+3p6uyNjpHg4eOnqa2nqayoqq1+f4DZ29yusLKtr7F3d3jP0NKytLewsrVzcnPCw8W6"
    "vL7Bw8RrbGu1t7hpaWlnZ2el1EWzAAAAEnRSTlMAAAXwEBTADS7BBDIDwcHBwj8ohG/AAAAA"
    "h0lEQVQI15XPyRKCMBRE0RfgkQmUQUAGAZkR+f/fM4lUaZUr767PrgH+z7Kj+HIUR7YFTpJm"
    "16MsTRxANy/K6qaqyiJ3ESjjddPeVW1Tc0ZBoORdP4zj0HdcogDiofSneVnWyZfoESBaTo9t"
    "e5711qAl2PfAbANKWBgys99ABEWkgnzgq58rLz8pCg7Wj25qAAAAAElFTkSuQmCC")

expand_all = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAQlBMVEWQobeQobfk7/zP4vfY"
    "4u6su8y5ydyrucvS3OfG0+C0xdedrcKvv9Gbq7+qusuZqb2ltMWXp7uhsMCVpbmdq7yUo7d7"
    "y3icAAAAAXRSTlMAQObYZgAAAFtJREFUGNNlzlkOgCAMBNCOG7ggInL/q4oyaRTeV9MtIyIC"
    "JQU60kZP2qhPGu3TgcDxONH4LMHYeaHZmryEdVNrOXI7OX6FP15ecyCcWfjkQryu+MuJlFCn"
    "ZXEDgAUDtdHbubkAAAAASUVORK5CYII=")

folder_search = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAABEVBMVEX////ZkQLYkALWjwLS"
    "jQLPigLLiALVjgLUjQLXjwLBgQIvHwHbkgLbkgLZkQLZkQLWjwLSjQLPigLLiALHhQLCggLP"
    "igLWjgK+fwLryWvPigK5fALTmybIhgK0eAPpyXi/gAKkbgPDlzqKXAJwTAOUZANwTAMAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAD9/v7u9fXd6+tByf4utvT/867+8Kv97aj756L76aP54535"
    "5Z/235j23pbnuE7w0YHz2pL24Jnwz33sx2n/86/+8a345Zjjsknltk3nvmDy14X65qH65aD6"
    "6KL76qX77KbcrUb235f025T44ZvftVfx1o3u0Yfu0YjnwW/v0Ibuz4Xw0IeEr6VyAAAAL3RS"
    "TlMAAAAAAAAAAAAAAAAreVx7fYCDhoqOxX2SyVWWnSOb7HuoyEWLtpMeEAYWGhcPCGYG/DYA"
    "AACfSURBVBjTZc/VEoJQFEDRI9hBGdjd3SIGJna3//8hXnW4Oroe99sG+KV6MVuezCqCAIp+"
    "KRRL5QpNocBUa1iVIUlg6w2szqrVwAlNTOA0GrCKLUy0anVga3feupLUs+kNYO8PhiNkLMvy"
    "xMHz4JzO5gtkuULWLjd4Ntsdtvf6wH84nhTnQNAIocv1priHIyaIxr7EE0lIpTMf2Vz+7/4B"
    "4PgqSGOZamUAAAAASUVORK5CYII=")

Folder = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAACK1BMVEUAAADVUwDbXwvZYBDZ"
    "XhDbXw3VVADXZBbCTgSLKgmLKAH65bb76LP85bL43qjZZxbVbi7//9T/8aj/76b/+bHSYhTC"
    "XSj/+7//5Zn/4pj/6Z3ZgUjNYCvSbC3Ray3RaizQaivQay3RbC3TbS7/+MD/4Zf+35X/35P/"
    "77T/7bL/67D/6a//5qz/5Kn/4qf/4KX/4af/5anKXxv/9b3+3JT+2pP+2pH/2JD/1o3/1Iv/"
    "0Yf/zYP/yH7/xXb/xHb/y3vCVhS8Win/9L7/3pX+2ZP+04L9yXH9xmn9xGf9wGL9vF/9v2r9"
    "wnL9xn7+xXz/y4C7UhSzVCX/7Kr+yWH9wlP9vU79uUr9tUb8sUL8rj78qjr7pjb6ozH7ojb9"
    "rU3/wG+3UBT/3YD+v079vVD9uk/8tkz8s0b8r0P8qz/7pz36pDf6oTP6nC37liP/myWsQgao"
    "TCX/24T+u0z9uE39tUr8sUX8rkH8qj76pzr6pDb6oDL6nS36mSv6mCn/mST/137+t0X8s0j8"
    "sET8rED7qTz6pjn6ojX6nzH6my35mCn5lCX7kiL/lSCmPwajRyT/03n+sUD6pzn5ozf5oDP5"
    "nC/5mSz4lij4kyP4jh75jR3/kh+iPAWhSij/34D/vEH/uEP/tD//sTv/rjb/qTL/pi7/oSn/"
    "niX/miH/lyD/miD/nyKgOgbCcDPJbSDGaR7GZxvGZRrGZBjGYxbEYBTGXhLEXBDEWxDIXhDB"
    "WRBMjSt1AAAAC3RSTlMAU+vj4+td/Xyfoh+p8e4AAADkSURBVBjTY2BAB4xMzCysbEgC7Nw8"
    "vHz8SAICgkLCIqJIAmLiEpJS0jKycnLyCopKyhwMYiqqauoamlraOrp6+gaGRgxixuompmbm"
    "FpZW1ja2dvYODI5Ozi6ubu4enl7ePr5+/gEMgUHBIaFh4RGRUdExsXHxCQyBiUnJKalp6RmZ"
    "Wdk5uXn5DAWFRcUlpWXlFZVV1TW1dUCB+obGpuaW1rb2js6u7p5ehr7+CWUZEydNnjJ12vQZ"
    "M2fNZpgzd978BQsXLV6ydNnyFStXrWbgXLN23foNGzdt3rJ127btO7gwfA8A7utFsqJRNV8A"
    "AAAASUVORK5CYII=")

hdr = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAQAAABKfvVzAAAA/UlEQVQ4y93UsUpDQRAF0BN9"
    "hogGJDYpFQRbf0DsrDTEyso6lYWST7DTWis/wPZZiZ34A1orgiIGwSAGIUR0LXwJyQuGpBNv"
    "s3Nn584Mw+xmBCMhIm7bLQ11DeQV5GX7w0siKGWGyx4HxkZr6D8JyoKF5JxTFnx5dmw68QVv"
    "9gdXWLFlzVHClh2qDhY8OXNgUw7UPGr+XESdkCvBeI/ozoRZcG3SbrrCuiU7PYJ5H17AhkuV"
    "tODejVqHFa2qOkkaubVnMd1SLy7Undru8HMPbTPEQy94HIQ/uxoD8T7zi6BV/Ox7efUcU6/d"
    "nq6xZmv6UGimPVEyrqGRGfWb+QYfJj2C7oWxJgAAAABJRU5ErkJggg==")

imgctrl = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAQAAABKfvVzAAAAo0lEQVQ4y72U0QrCMAxFT0Yt"
    "ggykL/pV+9h9lYIMYQhSkPowdGGds2Foni4h9+YmNBUSpnDQvnCkp6MHagI1Pi9vcACNlKm3"
    "CSqbodWE9B3/xFLSPQaCL6CJJsRcabZPoSUZ9VcOrZU+2qtMxt6lYbH0AMBGEy6Lg57VJv/+"
    "+MwEmcO3vc4rQjw+ssvrtrC76owboT/lBsJ9mnEw3GppiPWbeQJ25B/kbFs5iwAAAABJRU5E"
    "rkJggg==")

info_16_2 = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAACOlBMVEX///9ggsKApegAAACO"
    "su+Osu+RtfCYvPOYu/OQtPCOsu+Osu+QtPCQtPCOsu+Osu+VuPGStvGOsu+KruuNse2MsOyJ"
    "reqJreqGqeiGqueEqOWFp+WBpeKCpeF/o+F7nt12mdh4m9p3mtl5nNp6ndtvkdFwk9J8n913"
    "mthsj85sjs54m9p2mdhrjcxtkM93mtgAAAATGCJlhL1pi8pihMRkhsZjhcVoicZbdqcAAAAA"
    "AAAAAAAAAAAAAAAAAACcv/Smyfmv0fy51/y62Pukxvitz/ujx/eawPOQteyNs+qZv/Krzfup"
    "y/mbwPOXvfKPtOvT4/r////R4vmOtOuWu/GZv/OmyPebvvKew/WVuvGUuvGPtOy91Pb3+v66"
    "0vWNs+ySuPCSt++dwvWVufCgw/WRt++Rtu+CpeCBo9yFqeOPtO6OtO6Os+6dv/OKreeavvKN"
    "s+6Nsu3G2fa90vWLsO2LsOyKsOyKr+yYu/GGquWPs+yJr+yJruzE1vT8/Py6z/KIreuHrOuG"
    "rOuMsOx/o+CJremGq+uGq+rA0/L5+fm3zPGEquqEqeqDqemIrOmGquiBpueDqOm90PD29va0"
    "ye+Cp+mBp+mBpul/pOWEp+V9ouF8oeKApeeBpuiApui7ze7z8/Oyx+2Apeh/pOd7oOJ5m9p/"
    "o+R4neB9oeSt0PK12PSsz/J8oON4nN97oOB6n+F5nuF3m955neB6n+J2m956nuF2mtxwk9R5"
    "nuB8oeN8oeR7oON4nN5sjs/Y2qj6AAAAP3RSTlMAAAAAA2m++PG0TifMsRU5+e0eDe/RhVfb"
    "vxPvK/sW8fDTqoce+ewFav76PU7b5SsBA7Da5ubm8KcGBwIDBAWZ2/pgAAABEElEQVQY02Ng"
    "AAIWVjZ2ew5OLgYo4OZxcHRydnJ04eUD8/kFXN3cPTw9vdy8BYUYGBiFRXx8/fwDAoOCQ0LD"
    "RIECYuERkVHRMbFx8QmJScniDIwSKYmpaWnpGZlZ2Tk5uZIMUnn5OTkFhUWBxSWlZeUV0gwy"
    "lVVl5dU1tXX1DY2NTc2yDHItrY1Nbe0dnV3dPT29ffIMjAr9E3onTpw0ecrUadNnzFRkYFSa"
    "NXvO3HnzFyxctGjxkqXKDIwqqsuWr1i0ctXqRWvWrlNTZ2Bk0tBcv2Hjps2btmzdpqXNBBRg"
    "0tHdvmPnrt179urpMzExMDMZGBgaGZuYmplbWFpZGzAwMDExGVjbWNva2dowA9kA2nxR5tjU"
    "uw8AAAAASUVORK5CYII=")

open_eye = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAACZ1BMVEX///94eHkABg8AAAAG"
    "AAAJCQoBAAICAgIgAQCAgICbm5yop6itra6VlZWAgIB5eXp4eHl9fX65ubmhoaF4eHl4eHl7"
    "e3zExMWcnJ1gYGFOTk8yMzZOTk9sbG14eHl4eHmsrK6rq6xXV1h/gYPBw8Q2O0KMjpBLS0x2"
    "dnd4eHl4eHl8fH1dXmDm6e3Y3OFGRkdwcXK9wcbO0tbP1Nltbm1uc3a4vMHU2N65u792eHh4"
    "fHdZW1+WmZ7Y3eHb3eKpqax4eHlzc3dfa056eHVhZGFQVFicoaTS1dre4+eusrducXN0dHZ2"
    "enhxc3x7c3p7fHt3e3tgZGRWV1pcXmJqbHJucHVvcnddXWFvbnB4eHl6eHx3dXZ7ZnGmpdWE"
    "YoZ5eH54dn16e3t6eXl4eHp5d3l4eHp6d3d3eXl4eHl3dHt2bX59enrcAP+fjpBvbmdtdG12"
    "dXR2eHZ2d3p3eHd3dnh4eXp4dHl5dnuAdX+AdHSWlWgADAcpWmtbY39uaXN4b3Z3dHJ2cn13"
    "cXl1dHV8dnaAd3dubm1QQb4BFwsbHVdTTnJvYohodnhqd3Z4b3Rzcm5wcHBlZGRGC/YFBQMf"
    "CRKHLllxYV5gbllmcmZXgHxXbaOhoaHV1tbX19fMzMy0tLSHh4h8fH14eHnHx8dVVlhMTlEz"
    "NTmRlJd+gYZUWF4lKjIDCRLz9PamqaxgZGk1OkETGSEABg8GDBTx8/To6+7z9fajp6otMjkj"
    "KDDw8fTP09bU2d/R1djs7u8oLjWVmJza3N/T1dfj5Ofd3uBTV10VGiIvNDyUl5vd4OPa3uHo"
    "6u7k5ejp7O8G7po4AAAAm3RSTlMAAAAAAAAAAAAyoNvr5MmEHhbF+/ZvH+7f6v385eF4DOTY"
    "0879+4vK2yR1loDphpBdXfidQDy9/IZNGGad7vOdhSsGKWSKrOL1yaSVUh0MKU12k6S4ubiq"
    "nothMhICCh42TmNzf4J+dV49HggBAQcSIC8+SE9SSzsmEgUCAggPGCQoKiskGAsDAQIHCg8V"
    "FhMNBgEBAwYHCgoGA/bSB2QAAAEGSURBVBjTY2DABji5uHlm8/LxCzAyMgK5gkJz5s6bL7xg"
    "4SIRUZCAmPhiCUmpJUuXScvILpJjZJBXUFRSVlm+YuWq1apq6hqaDFraOrpr1q5buX7Dxk2b"
    "9fTlGAwMjbZs3bZ91YaNG3fs3GVswmBqtnvPzr37Vm/cuHH/AXMLSwYraxvbg4cOHzl67PgJ"
    "O3sHRwYnZxdXN/eTp06f8fD08vbxZWDy8w8IDAoOCQ0Lj4iMio5hYIqNi09ITEpOSU1Lz8jM"
    "ymZgysnNyy8oLCouKS0rr6isYmBmZqmuqa2rb2hsam5pbWsHCgBBR2dXd09vX/+EiZMYWNlA"
    "IuyTp0ydNn3GzFkcAJrBWXKa3u4nAAAAAElFTkSuQmCC")

PolygonIcon3 = PyEmbeddedImage(
    "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"
    "SUVORK5CYII=")

RectangleIcon = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAADsAAABBCAMAAABYQiwmAAABhlBMVEX////7+/v39/f19fX5"
    "+fn9/f3x8fHp6env7+/t7e3r6+sAAAC61v+20vquye+nwOWft9qXr8+QpcW20vmXrs+vye+X"
    "r9CQpsW30vquyO+nwOSXrtC20fqnv+SPpcWYrs+vyO+mwOWft9u20fmmwOSYrtCnv+WPpsWm"
    "v+WuyPCQpcauyfCvyPCQpsa1tbUJCQmgoKA8PDympqYBAQEoKCgmJibg4OAgICAkJCQCAgJY"
    "WFgEBAQMDAy8vLxZWVkDAwOVlZXV1dUUFBQGBgY4ODgQEBAiIiIdHR3m5ubo6OgXFxc3Nzca"
    "Ghri4uKbm5uJiYna2toVFRU7OzsNDQ0WFhYhISHZ2dkPDw/Hx8fMzMyamprk5OTFxcWenp7e"
    "3t7KysqCgoI6Ojq+vr5dXV0FBQWvr6/AwMC3t7ePj48TExNDQ0PPz8+Li4sbGxscHBydnZ2r"
    "q6sjIyN0dHQtLS1SUlIfHx8lJSUuLi6oqKhMTEzR0dFWVlZ8fHyysrK0tLTIyMgKCgo2NjbD"
    "/y0vAAAAC3RSTlMAAAAAAAAA7iJmqpnVhK0AAAIvSURBVEjH3VZpV9NQEB3rAjKmedqmmjYV"
    "uoBVUZBnwVqLYKGCgra4oXEXF8R935d/7iRpQI/Hcrzxk3NOTzLJvZ15k3uTR/SPgteNDtxt"
    "fwwjbqrtOzBuQrhJkGtYpkrtxLi77LTKROg5A9Z14mmVBLkJ6Rmfc1aldoNcmXMS5Bqy3gzM"
    "NVUvqo2+HPyMDDtCXcvMo8+3YBdVP1i3YKVVLzhnx/MvrGd8zgVrQGX2gHWtHDwrR3zUD6+3"
    "iGvDLuVRHyX2FvOojxwrC6/X82AKXW8c94JjR/gueO9nVBt9ZgRdDajkPvQdm4W9kLBKsCZF"
    "G3l0Vka8hH8H94uPUK7MCtVGQfwLeyGCJiPpeVB8dADVcxqvG2GPZESo6wzm1tkjRdjH/q9x"
    "kH9JmIeGOyE6cWnDoSGYSyOaug5rXe4mGh3T+ghVpJmRo1U+VpP745XjE0STJ7g+zj48xHpJ"
    "bGqaGidnZk+dJpqbm4+dCf79bHNjoyWnC5sWzhGdv7D14qWAG2Il0awXu/gy0ZUquXz1586u"
    "aTm97vXl8g2imz43xPqw2dat26y9oBqvrerOktZBIfn5N+76aYgNYDW+x65PmuFF73BfLjb5"
    "webhVa7rFQvqum1su8Tyw7HyKK08Inr8xI09pUnpcIWfbWmscqn1vLs5HaQhNuC+qMy/rOj6"
    "K5nza63fEL3V+t0UV9+vcT8sc/1jkPa0sX8Vn5YwMX7+Ql+/fce4E1XW5R6M+3v8AOFOlenn"
    "x/fcAAAAAElFTkSuQmCC")

refreshlist2 = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAACT1BMVEX///9OfjtRhD5OgDxO"
    "gDtOfztOfjxOfTtKeDk1ex1Cfis7ayolWhlIdDg2gBs7bCkyZSAzaSBGcjY0hhlBjCZlk1Rr"
    "k1xOgDtBkyJKjDQxdRkxbho+eilFgC9YhEhhpUhOnjFyrV1mo04wghk8fCVdkUpOgTxNfDtF"
    "ezFXpTtWoTlAlCAgbxk+hSV2o2VRhT5smVtKezdFezEhbxlAgihUiz91n2Y4ciQlaxlDiilz"
    "oGRXj0F6o2pHgzI+eygkdhkvcRlPlDY4bCRXlj9Zj0Z+p29Pgz07eSUxchlHgDJUij9LhTRX"
    "kUGBq3JPiDtYkURbpj5PnzI7eCNHgjIzdxuEr3VRjTtTjTwxexlpnFVAhCgxexlYk0M5gh9a"
    "l0QwfBlQkTpfmkc6hR5hpUhenUZgnkdppFJqpVVlok5enkZdnEVRljdbpj5mrU1orU1bpUBU"
    "kT5AiCdrrVOx1aLE37q52aup0puTxIFzs15dpkGnzpfx+e/Z6dOWuImMsn6oz5eDvG5cp0BS"
    "iz5nr0twqlr////+//2mzZd8tmhbokFlrkuyzai+3bOu0aBjpkpgqUXQ48fJ4cBXpDtamUGW"
    "uIvd7dZ9umeczYtapj5IhDK917TP6MdnqU5dpUNiqUnV6cyw0aNUnTlgp0ZfoUbf79jN4sSL"
    "vXdWnztiqUdjqklPkTbp9uSOuH/W6c+byItWoDlUmDtVlTxco0FxsFlsrVVPlDbO48e52KyL"
    "vXhrrVVsrVR+t2mHu3SDuW9gn0iXv4i927LD3rm21qmpzpqRwH8W9QqJAAAAa3RSTlMAC5n1"
    "+/vnhxCg+/g0Zoj9jvD9Y/79/f3P+kwJCpr+DGD4+y5A+P32mQEIIAi3/v399VQh4/395CFZ"
    "9/z9/b4KJAsEpfj9+Uwm+vl4Fv3+oQoEP/je/fv7lPzufPzNViD0/qIIbN34+fXDIsrxjx8A"
    "AAEDSURBVBjTY2AAAkYmZhZWNnYOBijg5MrOyc3LL+DmYWDgBfL5CouKS0rLyisq+QUEhRgY"
    "hEWqqmtqRcXq6hsam5rFGRgkWlrbJKWkZWTl2js6u8QZ5BkUFJWUGRhUVLt7evv61RjUNTS1"
    "tIEm6ejqTZjYPkmfwWCyoRHEMmOTKVOnmTKYTZ8x09wCImRpNcuawWb2nLnzbO3sgXwHRydn"
    "FwbX+QsWLlrs5s7A4OHp5c3gw+C7ZOmy5X7+AYFBwStWrgphYAhdvWbtuvUbwsI3btq8ZWsE"
    "A0NkVHTMtu07du7avWfvvligSXEMDPEJ+w8cPHT4SGISzLvJKalp6RmZWSA2AN7cTAld4BHn"
    "AAAAAElFTkSuQmCC")

select_all = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAA/FBMVEVVf39Vf39TfX1RenpO"
    "d3dLc3NHb29Ea2tAZ2c8Y2M4Xl40WlowVVUpTU0YOjoJISELKysAAAAAAAAAAAD////+//9E"
    "zP9Dy/5Cyv1Byfw/x/pkhuw2vvE1vfA0vO/8/v6I7v+F6/yE6vtZe+F1wPN0v/J64PF43u/5"
    "/f1kzvWF0uuD0OlKbNF2sel1sOh6x+B5xt94xd73/PyG0uz6/Pw6XMC/zva8zc30+/vJ2trH"
    "2NgsTrKett6dtd6+z8+9zs7x+fn1+fkkRqu8zPXu+PgiRK3r9/fx9/cnSbi5y/Pp9vYvUcjm"
    "9fXu9fU4Wtm4yfLk9PRBY+fp+fni8/POO6r5AAAAFHRSTlNNZmdoamttbnByc3V3eoFphwkW"
    "Gi0kH3EAAAC/SURBVBjTVcrFFoJAAAXQZ2JjDtjdregYoIKBAVj//y/OYSV3fQGXA+BOO7jh"
    "yRBBzObyTKFYynjgLZOKWK3VG816q10qe+HrEKHb6w+Go8F4Mu344J+RylySFsvlQpLozA9u"
    "RYT5erOVle1uT1ccAgc2VFU7HjVVpYcAgid7nGXlzMYpiNCFDV2/3m5XXaeXEMJ3ezxk5cHG"
    "PYyIwYZpWs+nZZrUiCD6ssebYeMVRezz/fOJgY878EgkU3+SiR9H4SeITcvHYAAAAABJRU5E"
    "rkJggg==")

showboth = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAAAAADFHGIkAAAAfElEQVQoz2NgwAk2YQUgif9w"
    "8BnOQpW4IPALq0SXMSemxF8g3v5TCCjxE4tR/4WwG0VVCQQAS2ANDrw64LyfP7FK/Aw3No76"
    "hUVisc///66rsBn1+/8/3b3Ywur/j8gkrJa/ta/7h03ine5K7M4t4dHR0VlCVJDgSgw4AABw"
    "Mp4jiquMbAAAAABJRU5ErkJggg==")

showbottom = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAAAAADFHGIkAAAAgUlEQVQoz2NgwAk2YQUgif9Y"
    "AFUkfmNKPJpQNvkpFh3bOHXjtHj3YEj8lQz5+/+PlwKGxCMdkOJ5DK+xW57L/xch8Rshvo+9"
    "AeI0NB1bOV1+YfPHGrbgH9g8OJ859Q82ny9gbMIaJC8E9BaDwEdUib//J0Kj5yb1gp0YCVyJ"
    "AQcAAE7EpmRKlr9mAAAAAElFTkSuQmCC")

showtop = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAAAAADFHGIkAAAAUUlEQVQoz2NgwAk2YQUgif9Y"
    "AFUkfmOReJ33G6uOXw4MP7BJXDBlwCpxgdW6GqvEjdV/Z6NJwG1ESPxGddVs7JbTXOIvXh3U"
    "jg8kCVyJAQcAAEQmtCUilN0zAAAAAElFTkSuQmCC")

Star_icon_notenabled = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAQAAAC1+jfqAAABoUlEQVQoz1XQsWsTYRyH8ef3"
    "3nt3ibnWVlwsoSIFRbGIDg7RolLIKi6CuDm4C052iVPFQaiTOuofIFiEIgREEB2iQhTxULRQ"
    "uIY0JW3ansnl7n4O0cHv9Ayf6Qv/TSdit+2CWjXqgopRATX/QMtv1J/9XKpiOQ+ANaJapKIe"
    "QMO8eLA+t6+sCx1P3mBUyK0a+oRMaTRMF29zbcAs/bPNSXWkq4LY50Fz/uCY4JrJinPDSJmU"
    "oPD1wvxTEFW1zavmSU+GCIYSHjkpYO7UXtVaAPK9WH/bPp1jOUZESoHDTKD82ouWZx+eaAjU"
    "z7x+53iGAAeHjIBpChTx2NBPnx2VI/4PtislTtGhy29iDuDi4OJKuGZEZXXzsWrMe1x8fFLW"
    "SUhZzVaWhnNG96tfvRjINIYdUjzG2GRIuPvxcnqr1rf0RO9d6dPCYhmwRw7EbNyvvQSwogvB"
    "zrkSAyAh+3t5jH4blYGjx93xBPJCdGjZhA4ACWl3BCyUv6xdv5RNfShHdmartXI3vCnOLtnW"
    "CAiACj4JME4v0cXqzKNOaftkrQ3wB0i1pYXb+yoIAAAAAElFTkSuQmCC")

Star_icon_org = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAB7FBMVEUAAAD/////8e3/3tX/"
    "////////////////4M//qIX/YRv/ZiP/////////////////////npn/UDP/aiH/49f/////"
    "////////////9fb/CQP/PwP+n3D+p3z////+i17/MQH/XCn/Yiv/VzX+Z1j/OAn/djP/TwH/"
    "UgX/eTf/VQH9xLn3UDn/gkX/YBH+nGz+1MD5gYH1HAX+p3z/ZRnzQUr/XAvvHzf0Cwb+mGb/"
    "Wgn/VQH////5oab/gDv/VQH/VQHwICX/axH2FwD2HQD/bw/+Y0T/PQH/TxH/cTn/IwX/agf+"
    "nXz/OAn/rIv+1MD/+ff/////3+X/T1z/QwH/ZwH/8/T/PQH/hEf/cx//ZwH/iFP/dC//bSX+"
    "qYD/aA3+k17+pHj/r4f/TA3/RAP/UgX/fzn/bh//eyv+lFr+n3D+Rgb/QwH/Twn/jlf/cSP/"
    "bBv+omr/sIn/RgX/Yh3/bCP/dSn/hTv+qnj/u5n+w6b8LwD/Thf+mnj/YyX/TAX/TwH/Wgn+"
    "nmT+rID/tZH/PwP/Rwf/ZS//UBP/Uw//SQH/dTH+qHT2Nhz/bD//RQv/UhX/Sgv/YRv/Zhv/"
    "YQv8OQT/Qg//SxP/Uh3/VQH/WwH/lVX/QQ3/NwH/PQH/Qgf/hEH/fDX/VgP/bR1uPr88AAAA"
    "W3RSTlMAEAUFBAIFARfC40YIPgk8BgKlwQ4HAxUgAnb+9x8RDlFeXmCa/F5k/tgYCc70pzkF"
    "Mvn+0YzLJf78kAgPZfNLAbZ9DPFVNf3lsthECVpXJAotFZb8NAFH3+oWmAUuPAAAAQBJREFU"
    "GNNjYIAARiZmBhZWNgZ2IGQFCXBwcnHz8LIxsDEw8PELMDAICkXHCIswiLKLMbCyi0sISEpJ"
    "x8bJyMoxsLMwyCsoKimrqMYnJCapAbWKMahrJKekpqVnZGYlaWqBBLR1snNy8/ILMgqLknT1"
    "9A0YGAyNcopLSsvyyyuSKquMTRjYJUyra2rr6hsam5pbqirNgOaYW7S2tXd0dnX3FFlaWTPY"
    "iNr29vVPmDhp8pRCO3sHBqBLHadOmz6jrX7mrNlOYF84u8yZO2/+vJyZsxa4ggXc5s119/D0"
    "amuYudAbLODj6+cfEBgUHLJocSjE5+w8rKyMrGHhEZFRQB4AQkI/YvKlWroAAAAASUVORK5C"
    "YII=")

target = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAQAAAC1+jfqAAABhUlEQVQoz33RT0iTAQAF8N8+"
    "rVgEpTAXm5GBsDDXBMNDRUYQSVDgqS6BlJ26dJECCYToXJeCDnUZdiiqQ/SPQBDCMJCicJqF"
    "hbCRs2mzcvqJ2EU79k6Px7v9Iqv+n+r1crXDOSlpOZ9krzxe3yOr6NvuQc3BjLgBRxR9UHrj"
    "dN/U2qE3GRluSabVqHXHWSU/jXk3vdJ2bYqA5f50skmDkgEzBs1r0KglvvwIqsqdtZf22m3Q"
    "VwumRRUUZZSVEg9HO3JBeCYlLqdgk2O2OGqjvHF1UsIugjBdkTBq0WE5Nb44YNGYHX4JW6le"
    "ig35rIjvtmLYc0VMKFqpJViajbusWb0LUiqanFevWY+EP7ME4UjZuD0q+mXMaXRfRcaYOeEI"
    "QXhvxhP71Mm7YdJNBUmtXpkVZqmaGL91YjlR0m2Dsklph5x010f5py97iaxq3xUMx2KNjsu4"
    "6Lr3nvmm+GOlZTC/ZrE/5vbmzm2ipuy0YN7vF7qH8v+woO2ULu2iKl7Lvs2ua/4FUX6Op4hm"
    "pHQAAAAASUVORK5CYII=")

target_orange = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAB3VBMVEX/////XQX/XQX/XQX/"
    "XQX/XQX/XQX+VAD+VAD+VAD+VAD0SwD2SwD6TAD0SwDqQgDqQgDgOgDgOgDULQDULQDIJgDI"
    "JgC6HwDCIACsGACsGACgDwCgDwCUCgCUCgCGBgCGBgB8AwCAAwCCBgB8AwByAAByAAByAABy"
    "AABqAABqAABqAABqAABqAAD/XQX/dSH6wYT+267/fyn6wob/fCX/plf+3bL/7NP//Pf/gzH/"
    "+/X/68/+3LD/qV3/n1H+2qz/+fH+v3T/WQf+wXj+3rT/+O/+2Kb/qFv/Wgn7yY3/9en/um//"
    "oEv6TAD/vnH7xof/XxH/olf+3rj8zpj/kzv/q1n/7tn/YRP/7dX/qlf90Jv+2rD/ql//mEX/"
    "9uv/lT//hSv7x4n/izX8yJD/6c3/mUfQLAD6QQDOLAD/cBn/eR/+VAD/fSf/Xwf/6tH/smf8"
    "u3b+5Mb/9OX/VgPgOgD8z576wIL0SwD/cRvkMAD+4Lz/ahn7xIn8y5a2GgD/VQHkQACgDwD/"
    "gCu8HwC4IwD/ein/9+37uHf/Yg2SCgD/aBX5u3//eCe8IwCqHADySgD6woz/8+XEHAD/8uP6"
    "wIjuSQCuHQCGBgCmFwC4JwB8AwC6JwCmGwCKCgBqAABfys7jAAAALnRSTlMASKvS1a5RGMPG"
    "Hhvk6B7AzFFUrrTb5/D53uertFFXzLQh6usbFa63G1e39rpd6y+60AAAAOpJREFUGNNjYMAG"
    "GJmY9VhY2WBcdg59A0MjQ2MTTi4wn5vH1MzcwtLK2saWlw8kwG9n72Do6OTs4urmLgDkC3p4"
    "enn7+Pj6+Ph5+QcIMTAIBwYFh4SGhUdEhkRFx4gwMIjGxsUnhCUmJackpHrFijEwiKelZ2Sk"
    "Z2ZmgagMCQYGyey4nNy8/NyCwtycomIpBgbpktKy8orCyqrq8praEhkGBtm6+iL9hobGhoam"
    "OI9mOaC98i2tbe0dnV3dbT29CiCHKSr19U+YOGnylKnTlFXAbldVmz5j5qzZc+aqa8C8p6ml"
    "PU9bRxfMBgBcgz4JXsMEHAAAAABJRU5ErkJggg==")

Up = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAABs1BMVEUAAAA/p/IOlfIUl/MB"
    "hvOHz/ib3PkMiPEAffFwwfXs+f/Q7/5xxvYKf+4AeO9ou/Xs+v+s4fyI1/qf4fxfu/QJd+0A"
    "cO5cs/Lr+v+t4vyD1fmD0/l6zvmF2PpKru8Ib+kAb+1QrPHk+P6t4ft90fl/0vh3z/htyvdl"
    "x/dv0Pk5oe4HaecEce1VqvHx/f6/5/xwzvl6z/hyy/dpyPdhw/ZZwPZUwPddy/gumu0KZ+YH"
    "g+8xoO6f4/qT1fl80fhwzPhoyPdjxfZbwfVVwPZKr+03l982m+k+sPAagOUIZeULgu0lle0b"
    "j+0DeOq25/tqxfZUvfRRu/RKuvZBquoheNcOcNwQbuIWeOUMauQ3ofG+6vphwvREtfNFtvI+"
    "s/Q1peclguAxoPCr4vlTu/M7r/I5rPEzqvMrnugfeNwrmu+c3vhHtPIypvAwpfApo/Ehk+cZ"
    "eNwlke2K2PY9rvAmn+8mne4fmvAZieQTctshiOx/1PYype8dle0clO0Xku8RguIPa9ohiuxO"
    "w/Ygn/AYl/AVke8Pi+4KfeMKaNoPZN8JYtkJYNoIWdYGVNACTs4AS8sIUNMcZT8kAAAAAnRS"
    "TlMA+1z85qwAAAC5SURBVBjTY2CAACZmBhTAwsrGjszn4OTi5uFF8Pn4BQSFhEVEYXwxcQlJ"
    "KWkZWTl5CF9BUUlZRVVNXUNTSxvE19HV0zcwNDI2MTUzt7BkYLCytrG1s3dwdHJ2cXVz9/Bk"
    "8PL28WX08w8IDAoOCQ0LjwCbEhkVHRMbF58AtzYxKTklNS09Ay6QmZWdk5uXXwAXKCwqLikt"
    "K6+AC1RWVdfU1tU3wAUam5pbWtvaO+ACnV3dPb19/RNAbACmyCjJWy3OiQAAAABJRU5ErkJg"
    "gg==")

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

