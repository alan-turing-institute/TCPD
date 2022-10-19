#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the apple dataset.

This script uses the yfinance package to download the data from Yahoo Finance 
and subsequently reformats it to a JSON file that adheres to our dataset 
schema. See the README file for more information on the dataset.

Author: G.J.J. van den Burg
License: This file is part of TCPD, see the top-level LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""


import argparse
import clevercsv
import hashlib
import json
import os
import yfinance
import sys
import time

from functools import wraps
from urllib.error import URLError

MD5_CSV = "9021c03bb9fea3f16ecc812d77926168"
MD5_JSON = "22edb48471bd3711f7a6e15de6413643"

SAMPLE = 3

NAME_CSV = "AAPL.csv"
NAME_JSON = "apple.json"


class ValidationError(Exception):
    def __init__(self, filename):
        self.message = (
            "Validating the file '%s' failed. \n"
            "Please raise an issue on the GitHub page for this project \n"
            "if the error persists." % filename
        )


def check_md5sum(filename, checksum):
    with open(filename, "rb") as fp:
        data = fp.read()
    h = hashlib.md5(data).hexdigest()
    return h == checksum


def validate(checksum):
    """Decorator that validates the target file."""

    def validate_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            target = kwargs.get("target_path", None)
            if os.path.exists(target) and check_md5sum(target, checksum):
                return
            out = func(*args, **kwargs)
            if not os.path.exists(target):
                raise FileNotFoundError("Target file expected at: %s" % target)
            if not check_md5sum(target, checksum):
                raise ValidationError(target)
            return out

        return wrapper

    return validate_decorator


def get_aapl():
    """Get the aapl data frame from yfinance"""
    date_start = "1996-12-12"
    date_end = "2004-05-14"

    # We use an offset here to catch potential off-by-one errors in yfinance.
    date_start_off = "1996-12-10"
    date_end_off = "2004-05-17"

    aapl = yfinance.download(
        "AAPL",
        start=date_start_off,
        end=date_end_off,
        progress=False,
        rounding=False,
        threads=False,
    )

    # Get the actual date range we want
    aapl = aapl[date_start:date_end]
    aapl = aapl.copy()

    # Drop the timezone information
    aapl.index = aapl.index.tz_localize(None)

    # On 2020-08-28 Apple had a 4-for-1 stock split, and this changed
    # the historical prices and volumes in the Yahoo API by a factor of
    # 4. Since the original dataset was constructed before this time,
    # we correct this change here by using a hard-coded closing price.
    # This ensures that the resulting dataset has the same values as
    # used in the TCPDBench paper.
    if (0.2131696 <= aapl["Close"][0] <= 0.2131697) or (
        0.21317000 <= aapl["Close"][0] <= 0.21317001
    ):
        aapl["Open"] = aapl["Open"] * 4
        aapl["High"] = aapl["High"] * 4
        aapl["Low"] = aapl["Low"] * 4
        aapl["Close"] = aapl["Close"] * 4
        # Adj Close doesn't adhere to factor 4
        aapl["Volume"] = aapl["Volume"] // 4

    return aapl


def write_csv(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            aapl = get_aapl()
            aapl.round(6).to_csv(target_path, float_format="%.6f")
            return
        except URLError as err:
            print(
                "Error occurred (%r) when trying to download csv. Retrying in 5 seconds"
                % err,
                sys.stderr,
            )
            time.sleep(5)


@validate(MD5_JSON)
def write_json(csv_path, target_path=None):
    with open(csv_path, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.DictReader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        rows = list(reader)

    # offset to ensure drop is visible in sampled series
    rows = rows[1:]

    if SAMPLE:
        rows = [r for i, r in enumerate(rows) if i % SAMPLE == 0]

    time = [r["Date"] for r in rows]
    close = [float(r["Close"]) for r in rows]
    volume = [int(r["Volume"]) for r in rows]

    name = "apple"
    longname = "Apple Stock"
    time_fmt = "%Y-%m-%d"

    series = [
        {"label": "Close", "type": "float", "raw": close},
        {"label": "Volume", "type": "int", "raw": volume},
    ]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(time),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": time_fmt,
            "index": list(range(0, len(time))),
            "raw": time,
        },
        "series": series,
    }

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


@validate(MD5_JSON)
def write_patch(source_path, target_path=None):
    # This patches rounding differences that started to occur around Feb 2021.
    from lzma import decompress
    from base64 import b85decode
    from diff_match_patch import diff_match_patch

    dmp = diff_match_patch()
    diff = decompress(b85decode(BLOB)).decode("utf-8")

    with open(source_path, "r") as fp:
        new_json = fp.read()

    patches = dmp.patch_fromText(diff)
    patched, _ = dmp.patch_apply(patches, new_json)
    with open(target_path, "w") as fp:
        fp.write(patched)


def collect(output_dir="."):
    csv_path = os.path.join(output_dir, NAME_CSV)
    json_path = os.path.join(output_dir, NAME_JSON)

    write_csv(target_path=csv_path)
    try:
        write_json(csv_path, target_path=json_path)
        need_patch = False
    except ValidationError:
        need_patch = True

    if need_patch:
        write_patch(json_path, target_path=json_path)


def clean(output_dir="."):
    csv_path = os.path.join(output_dir, NAME_CSV)
    json_path = os.path.join(output_dir, NAME_JSON)

    if os.path.exists(csv_path):
        os.unlink(csv_path)
    if os.path.exists(json_path):
        os.unlink(json_path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output-dir", help="output directory to use", default="."
    )
    parser.add_argument(
        "action",
        choices=["collect", "clean"],
        help="Action to perform",
        default="collect",
        nargs="?",
    )
    return parser.parse_args()


def main(output_dir="."):
    args = parse_args()
    if args.action == "collect":
        collect(output_dir=args.output_dir)
    elif args.action == "clean":
        clean(output_dir=args.output_dir)


BLOB = (
    b"{Wp48S^xk9=GL@E0stWa8~^|S5YJf5;Ev@JL0teKV0>CMKFPfOjxe~QIT64tOZFjeJj%l`;B"
    b"amH0GxlrmpS<nf9+SitRxKpHG3{qgy`x<uF?Z=^6ZYmt{-@RZ3^b&8;@H?s(M*j+oo9EcIkq"
    b"&q9p+xLenHF8}SQq($c`MxOJxG`cqyU+fOCCXiB0HwyBM6&a|}3&`~iiwg5v<a818c-Z7LxI"
    b"@M5eiYBiG*-hq%oed8X3|2}BW<0Teu^hA1F!;p=@+FTTylZxa7eqj9i_qPBM(pzWc@^3v<F&"
    b"E)j(%5Gl>)!co^a*SMzZW?A7E?%W<p+#W(qnmw}YxYMVhJo`_m?i$gzVvg-uG;R`BFue41(I"
    b"uVm0O$hp#LX*Uc?#FCsge}vHMB}Ys`Am<hrtNCsCv2<X8Ex}B2YD-ZE8R&MQXj1yXjO;KqT?"
    b"y#Pd5Esz6|}xJ5Z+u8;(g%PO4#Hg1&x<NB^^*dLo}8mob~4Z=CIvGU1x<Aa&$+4oXnuRLjzE"
    b"mq%Zx+wtZ#~;oFx~G)&Fb=<0<j|IZeuOt-G%2f}~_Hjzs?2?l<Cow<qZFx#xNC$^ZyW8UC#B"
    b"(Ib}X%~rSoD&m{U=VZmR65LL2H2tF96(g<u`SCbLZ=*tF0Y;>X+sP#S{w8VTqfOngKo*0Qmb"
    b"470B-^2cHk_yHd?Tn=LDUBdk)oweNj$dEGf3S%X#-gQRZutB4aCPz0ij!A^~(2(6gd#8hv&y"
    b"&4>by!x|@Zl23=t%w9dXbgi&hEprgTEqZaJyk8piSx?$rQPmcqrFg$0iuNHHPg&^mt|PYH^!"
    b"G6*U#$YO@1esf;CGL_@=rR;sg}1SmXG?+0r?UOl@6eUo<L}KNxDo&3;EF9yA(aidQW4z`U17"
    b"=FA|@hgoZ~$0M@3XM<R(_0O1I*rg&M!A}P4q+jhi7TNq_LFc1&gy#;_>JI>i0v$hE?e4F&UE"
    b"{ZeRZP=jk-TpkB(q)Ch?xbi?;yTZ`<<5*iYv%51zhC|0rO%PkGLaI!z}T1qrCazYA*tGRDG5"
    b"*ga2v8vlKD1g-GU<}Qa`K}rC-FP0fC*K$;4*jWAlHqHmR89J0|aTUuJ?QH|>gMkhrC{xwevX"
    b"WxGygUq8m8ClFpsp6~NOpEOqzJWEN!FK4w?UsN_lq7F-jEoBaAmcl_9W-lwo&%=aHH$~5L@`"
    b"CPn$2n8`Pa*L%5ZpKqXN2%+^N7z~_wK4GXVmsYja%%qixFTmY#DGN8fPyjaogWl{hOmhb6L4"
    b"}M#5&iCoY5t(aRo!KUxcG<(5>jLA9a$Vx3xrAyZS=7DlcGw+u~$Lr)zsC>8Xb`>KHk8h_+`("
    b"=!vIEDh{<hl8}R9b6fgcf3)z=K=p0Tfs`{v%ZP4fZQhH3@X(D<6gFo7+3Otz>%6N2_zS#Wn$"
    b"KP4t8m2?7Ue3KNx=mB^pG!+WcU!tF!gNH8c%&jo>BI8(E;}sa^9Kh73mmMIBx;!vcnpu+9;2"
    b"e<ES){JVyu?B<~No}`!A%FLf2Xwgq9lS8CI3t+)T3bb@mvc2!Ub;EUzMn^;TdIrAieGI?JOr"
    b"dgRDw&-J<<(>CCV#~u*{%86*IJ~f7~hd{Ke|=iT}hZnLOR#eIh#xe`~9rYB>A)?Pmn&+mI1B"
    b"UK_Ml_GLQ&`gO-{GX<<3j@Ke?~+~V7vXjhn;teTWx$wPjiHBd3~%4M9h@Km)H221G@m`TSOf"
    b"m<NnA$B)K16;()!cXlvDvNI0%gq^!BjGkuw=)kuzdt_+PpC;3WQ1RV%pZ;VKS0_SRq{utNF2"
    b"QWTI)*vheTq=i<!S{%|QKx>Vv4<{T@s14;{#Nw{^XTWT+4RK8W9T0TAPbHOUfu7)5M)8spg8"
    b"%RhPvrnyvdrph9U{Bg?S^&%vNvX+fyJ&|zXq3+Tf*s6Xbfj&h2+Rb+3j6HzBREQbNMfHdTbU"
    b"Vj!46UM&C?g?Q!x?OG7&O!HD2fog*n3f#(VzWV6@b{&>Awy992;50L>$2<O$+%rqMp(c+9CV"
    b"{!+Xf{LTkl5%oh01pwV1x#P?WG+kuDoNRKJ!<dl}x2kRI~m?z8y?|;LPmmvTo7giQ{MEe$X>"
    b"7Q2`%wI!Bhsujc%619IDHmD~pAC_iV`8qULr4-5{Gc`eUQ92P01YmbdrN!tZ7^9=6q%lu*#w"
    b"uYs=`P(Ygs<b*TeZc#S$1Q4;j)^LYcRZ=0@I)HwDHov9}EQ6Ne6<OQk}FsKS*6*N>fdWp_O@"
    b"#)WJGzx>1*r$)(r!>Sa*sVKrT++x7<>U#5vEJsMe7_^s(gxcEz49_vQs96PMY0bls8KM4Otd"
    b"fwjZ>Cn?<?)QTbg?j1QX*8W(nIStDZ>YU?ok1-c(ciYpH7+d!a$sHgzVJdOy7^<a?4EA*|A9"
    b")xuSlXyANV!)pM~5MH%q(kW@^=-J?beiC|u)2>eivq(Yj_!`t7Z_}7jOt>5SyUIY|A1OtHrH"
    b";M^?N}8B7y~LOX&5$h??rW`xH(QOkY}!0)2Z|v<Qedk_lJy2QiX2W6gwLU(Go4sqW)1&DzhR"
    b"W9e%zVCzTZY|P)4^1**aW$N9o*|3ZZ(C)j95d25q%|gTJ_Lmc)1mxT_L#E!N;GmwKZdX^ECJ"
    b"bDSz*okP;bU;*_}mGx4HS@&bY@D?h#OBss#-{~q`ez{%BS13At+iiq}>$T1^ok!L&x|s3pd|"
    b"J`>C><APe#*okMLg5%NFM(Z92V}ob|VeCNdFt&Vg>QiBMDTu7t?%ON%6T(vq^@66xTr`Aq4o"
    b"bbm%T{)4u2ks)=Z<FdXZRUgYILu<Hxo5Ug@~5c+y3fm2ddW1KH!VsMYNNtmzH0m_A6WDfT+U"
    b"DAtMO)Mbjh^DVQ=DgZ@A1{Nh&WA9l8=!<i{2jr;=kb4w3qTq^s6tQzF)635K0DbanGtpa&Js"
    b"ejc=fGh^-4$_NPd&!Yv)-tIMTdAx*Y(@Qw4-t6Xp$Lu{P=wglKrOjXsUJ0@h5m`5si*f-eyc"
    b"UGWy^2Kd3TyTP0QBQuA;Rq>q<0eOa6SWqg;Gyu>}y)kRFDkBfFs!l&;?t(p7@*;PxqDIvBB%"
    b"AX97l0kQPlz-lfcPr$NU-MYjHis8&C5JlxPbfBQc@J3EQSAivq*p>(bJbe%v>|2WX_`osx|a"
    b"ziOtSu?c0qG2YS^hJ93N7f_7R|`O+Qr{yW(3><p!F!*pGP5Dk%bme4pV8p$bl^Hp$_<S=sDM"
    b"ewuTWf+r_1L!=a*Bxrh^Z5Li3~u?t`5j4Am>K%3c#h}S`H*H!&@LI0tN$(YB958;x>uv2J&@"
    b"P(WB?{aMgx85@-J02Iw8oE`QKF`rk*I_a1A14DKs>a-uMo<qZQ2`D;dXqAn0h6s=R4FCal{W"
    b"I^X2p{ebiiQaF`tI-0@CiA{Na-7=GR{DwMnT6Yn{?l1``@NHE;s(nlr(W;WqaT$}_tH?rELr"
    b"B8Fb|3$N+ffrx0Z<?{Cxae%`mIoNt>z)X9mvr-DvMhp(A@WY!EHC{EmWfpUxX`K9Hn$4^~(4"
    b"@ubbi9EcPNgMC>SK3G<we!|ilVQ8X+Fd`|4C(y`363rk`0ZwXy<wXek>wgTWN`h!*~lJRbka"
    b"P87p4RqW94#!S}SwPw#X%kf&cZxCANu%RMI@eR0^y$C1{N12BrsUA}#tzMB{1U4-mOnjx0pJ"
    b"@JKF4@YNH<esoe<h$RgHe1KS<x}fF{!r_-IrdC-15~=vF&!0gWpyW*ucbc%8;X-!KdX|9EI}"
    b"-+tPClt^~_{+f*(dg7~6-p4mEu*fSB1*;pS1a@G_N$4D|e58by3@-O7jXeFA`N>ahIPlHYrT"
    b"fsa_6>rpm)~+$cw8A6Wt`(c&zS|z!=AE%TbgROrdJVe@>I^?tuZiPP|eR-weuj`*&RokYha+"
    b")nwMdihMlSVH|?O{Z+A2$j}5O)8JMDc#na{_@2Fx>e3QO(F5R-SkNk_gMmt5Qc@&tjwBJ<5("
    b"6evECo#>){$#Y@vlDLU`|BI>Qs;~|)2;<nIRQ8VtzAjUyzyzRixNu=wRzF2?I&sHTN|qQfHO"
    b"w|3eRB0w#22q0+&vxZ9u0;&jpI-%zK)B7T^pnAM#rEQ$(+!S=`tqix~#J2caf#r{uu?=P}$k"
    b"QGIxbNf|q@^$O_8QKuQ)g9#5hEqW}gXS3a@F)mizh#F~$u;?(K)Ek~x1hjmborB<tb(>?u*j"
    b"x0hTXL$U2fO~=n&1(^!JV|?E>m}bQAz)Lv;0}{stEehDw71LN6mEO2R99o3weq8_Mfp*7Xyp"
    b"4W*?0q_I0pGC)3*Y6OdhfoDre2=9*1*O@CO?2yCe(tub|HOSW`WM3WD^hGuW!aU?xbc^H=Fv"
    b"?$9_jBvk@r$}zwLgZ)uTCr-N{n}01KVE?#X&i<ySlZWo!I$8`MluF!fa4COxaAvxMjtzzNf`"
    b"4G9%^!H704F{RXvkNQx&#1-lUfY;9zInkfh5DAf|~j;hxZu$b>z&?5gt;uz3Hj$9`<u9sGQ?"
    b"+Z_niu8hj)HK!9XkU6XRvr&bI<z?q1p2=P&aqQ!iXVe<lh%f(&jadBdWZVnF#<4rZJ3DE8>&"
    b"J+*GH-KZGm>J|3JZXV{+zL3PSSKB%{g{bYE2?h(qbx}OSs~!#{w?u%Q0Rdv969f)$L)IEMJQ"
    b"TBX9V3$2~237)n{Hs>iq1a2x9I6SyH%Hmn8yTvjI_G@8Etj`ppZ&dm7%`2xk($`b9>O?;m07"
    b"$0W?ak=+MVE8?QB=}-PH4EY4G^QrZ$95@AcH{443wRaC;Ur1)MUy1%t@Tq_`I^H)R7EDiVrW"
    b"d0AyZMz!;L~T{P-2wx1p>TwsU^m*Q&4R6JT>8d@yxcc!t~)eXsN#Ate9m7TFpMrvU0@DqNUZ"
    b"1m{M=&^h64vVx<O4I`(uhy%Qd=`Uh^v%3ouV7^ptFG>{e%>d{fVX2M0z8BzVVJP3X*H}AZ<J"
    b"($18jF-JxHZWKYqe{;<ov43!S@XCmB<DpvU-}0g(9$1R&9N@SaDqd_<fOjJ!Algyw81#W3dU"
    b"5FT+l4dKV8D0dytCPEz$AB&B7Pak%?BryPBZTvkFHN7XD|=G9anWGJSMlhHiktAJ<{UM&ijV"
    b"{<IVSFCz0j!7hi0mUbdZ0K=3QFMAS%JgbGNPZZXHAJkP|F36q#`egm*`Jo{r80P}BvQ>f-NZ"
    b"S-HRV8cm(g;9aET2x9>jIq(iG%(+UbVxvIvc%8y%@&BpQF!jJX%xHNV`Zlr6}RyI1cYK?+s?"
    b"Ny3~>#QU;pWkakTq8X~=?k7A*i_W1qE1Hu8-@WKS*K;NWekZ5ThD7s?6-U2aEy-%OQjWBAbx"
    b"pI9T7FWcAJWc6KqHa-E1<<)xm65-`O<r-a`e!6dc6T!=S!<ua<Vzh?-1N#VJ3M-i1se_$X1I"
    b"@8SR*)v2vubq5PtqT}Ky6<bK6ov9iD+Ukiab@<_U%vC=Ig3fr#!fO+q)2=~9M%#YEKBvP<k_"
    b"~H;jx`4d=1F(b&7AFnEIRgcfthnu{tmAs^Hu<h`mSnXcpo`xm;}PY*@m9upcR3UdkMhO}ll8"
    b"k74*c+_^sbv_)eWsGYR<g-i};%WpO*Re2aQ7Re7=|Q>dS%=4#K-VTF9_BZavHENNuTX9UOZ)"
    b"9O$miSJQauagM%b7Z-K3a=^N1Cl}F&$h~baz42+?<1%Ey%0^qI-AO-EfULbU<?Ei82n<GW)#"
    b"t%<BiBMPI0;MyE+gPKpO=B@yx685Xzy!1V>`3>KTtDG5b5#*a+X)?IuoN37fq9nB%YV^6Fhg"
    b"ypQ<90;nMmBLik>VzmYn##?sNGAIug(^>zDgY7xBHjx)HO7Tk%5(Gzxx3kRoYWv@2J(M6S-9"
    b"PEFuEr~{F+X|J<+>RJ4Oa)PqiZf1?b0fmJo&P>Vb+o-Pue#QO<k~`mwg0j|Jv{&Lv`Pshndy"
    b"Hnuyf)8K}W<<ru=kEIig2os&+%XKeppJm;fyd7cWwcLzEaDxlWU9AYb_U%MKDBV;P@qwoeh1"
    b"ytpF|ef6__SGgg-2XGc8h8fn+UXKTFFt}V8%PzAS6=b?Y(bDYFzCCL(HaYZ<Fitly)l9?|M;"
    b"KC8zh7D=*H10wci1q7sFt;jbkD<H_<@Naku1HvMd26}E$x7dV7HK;U{&;#@@v~8gvsSSMiNY"
    b"g!A!on?7kx!ANx>z-hV}yF#}XfI&&m!wWNh^){$ZVm>jmRtDHbevBw#o_NJ4W4)POR$3g}w4"
    b"UTa`iE1#2f}~!kSUDZl^K9b6hrh3G0P1`dmx4oDvC35(bfW-MnWPx-|4T{sh4Rs*<vHN9Oe^"
    b"Vc`<<ZuTA}T}td&ssv-*xdR)grr&$v`*$|^uBSaTw?68ywi6dC>{#%J)#;^#x%NY3V6p^HiP"
    b"YlIl$iOWHToMB(KleJD%N#k168gwwpI?XiVJlnhm>5aLBK|^OG@z&^LMA=(N(P(IZdZS)ZK2"
    b"iI5F>JD=00000TO!Fq)kn{C00G@5=A8lnO;(*3vBYQl0ssI200dcD"
)

if __name__ == "__main__":
    main()
