#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the ratner_stock dataset.

See the README file for more information.

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

MD5_CSV = "db7406dc7d4eb480d73b4fe6c4bb00be"
MD5_JSON = "f7086ff916f35b88463bf8fd1857815e"

SAMPLE = 3

NAME_CSV = "SIG.csv"
NAME_JSON = "ratner_stock.json"


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


def write_csv(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            sig = yfinance.download(
                "SIG",
                start="1988-07-14",
                end="1995-08-23",
                progress=False,
                rounding=False,
            )
            sig.round(6).to_csv(target_path, float_format="%.6f")
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
        reader = clevercsv.reader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        rows = list(reader)

    header = rows.pop(0)

    rows = [r for i, r in enumerate(rows) if i % SAMPLE == 0]

    # take the first 600 rows
    rows = rows[:600]

    name = "ratner_stock"
    longname = "Ratner Group Stock Price"
    time = [r[0] for r in rows]
    time_fmt = "%Y-%m-%d"

    values = [float(r[4]) for r in rows]

    series = [{"label": "Close Price", "type": "float", "raw": values}]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(time),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": time_fmt,
            "index": list(range(len(time))),
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
    b"{Wp48S^xk9=GL@E0stWa8~^|S5YJf5;L{ZjLR|nLV0>CSo{B31X6^{N_o*r}*X(N!3<0PP%R"
    b"7<`*fGvbvx&%h+w-y>*=dd)k`bQZq)bG{qhn1ETPls#*1gCEp6nEu0>;P-FoXdWMI*llU1IE"
    b"WewFQ1W~l_Df>UIAzArs#>@nW5XhtZGI@)~iW~+r!<t3?OUF5-C-)}8izNsrnIBBZ0NPe~kp"
    b"Ro{kN(q971Q{iJg2Eztz=egBOAmsQiMfzTbM&60yz7`~FB1@M9^~?3;mdpwy7x`<Ih?AP)Te"
    b"{siv33sJe1|y?D!EPVsa~1WDBzKMG-S)F1`J(8mU%O1^!D+3BPV!M)6rSDP~tshv;BGOf?aL"
    b"z$LpkO}M;FFI!b*rwjM=H_O~5p{qN3Lyfa9wAB1L%l+w{G~;OdUt!A}cJWETpJmH?JfhJ}%T"
    b"ofX^Zx+O4V)y<DCpsba*+h-qk-3GDspDJZiTs9m$&6KK#WK-Mi8BrH)3pL+DXg3Io=;rAOmb"
    b"yW)CLntvNuP_O~=^cm}tkns(|9ZGFG<bl0jTNnHJW@;?fX*yw)?Au?{trSy6XBj;B5vdS;({"
    b"~kg2T~yJtA*5x52g547!f>hV^d@w!)p%r%*`oOYG9p8$WLK|7lw>Iv&2SP8so!np9<RzA72D"
    b"#BS=PdmAEqcLyB9h>sAfJs4MxwHow0Qud6KUD4B)Rc`MKOcq`m(X8YQ~sJ#C7y)~sJ@8Boa^"
    b"s27H162Ji0Et!J<xt%<6!mbsE)-!o;##0_m#V%absbFVhaInpl(mPIT`&=JcJ5X6Pr-|-rCf"
    b"*Mhn@vc7<ruJOteY1TFFvw<{c6(`6-^5D>WdaD#bk|oKsh|##Q&vgO`@9z!^%RDcpq(lR)cl"
    b"1ad+T&)YFgiw4}_@_jPZGS~${$US?2XoC6BCN$!}?cL!`GZQ-Lh`w*=!WpixXWmH4y{o2uNd"
    b"$dVk1z@htm~hM)Dh6cnv4VN(4Wn0v#hx=@^v%k>RS9uE?-L-qQiLE%Z0B5O_vjK$45jYHg2t"
    b"LEbhW)1e+nte0DwTeSS6_Kicf5aFSc<(P^7WI4o(a#igMjugb<b|al3PLo1=}88bj-T-+>|E"
    b"WT`N%mn{ST5!!sF?nn;j{qPU^UQ<8nh{*07cHT&qD=FQ1!S>{*Cj{*=D4M11tPlLJEuaLd`="
    b"g*KopKCsIB}`Vz#lp*aZ<nmSkWA)O$4ZwtiNH=vypU;<aQ7Pc=28p!jAb`OaSCSnO*AsW(Qq"
    b"U%Rr0kra>_UYgPvfQ`1@0-&KCRrMy;yTCrGkdfu64mWzP~ru?3%q$tWAhAdK~i63l>@kcO34"
    b"?*}DuIv3a#H0O{=;($&-vM_)DwwEhmKZeGekLo*G^^w#x#nd<v{>6%@B-m&SycKT(G^bz#cM"
    b"u7N7!)c({<H5F;SUWY|%S&*Ly{;!=d(rNyYLQCa8g8Iymhw`}xJGx@T1^Gh!B@L=jU9)Wv4>"
    b"hbPe$h{mE}dB~d!3^_~)M7hAf7rYn`vj^cpr}OqAa>VN|_;`p_sieTZ0gh>U#c^n2S@<tQSy"
    b"EFJZ68?jd1+~4n~uy)$cS+bXj{l$7i$7+?UuL2WWc%*ivcZ(Zt*XK=F^R##}GGKlHOY4v#sU"
    b"eIl@~uME0E)5EJ*JE!ywngrfXw0ucH?zPQLcCB~l_W-APmY)Wi*iF}z}`b~$JLXxM>)!Rr?p"
    b"}Lydca2N&PT7&$0dcWo99y#Y61Md1{XS0b%A*LBV8^d?p~1ef@K4hxjU&{xWy~ERyVbj({5S"
    b"Oz@gHR+nEeJYdcSFrES?FRYi(UWk0eU-_(gv&$6Nfxn+n|Sv)kM|vXGN5L+7SMT1naX^!Y=f"
    b"N={~Suy*MUZ{s6uCInAOMK}&a@Hb^y+O{V!G|?p(rXWl;56!w8zrK)s&B=w{Te`m<1aM(4_G"
    b"&X!8)~l}tvK6Qex{AC@4tnX&9eL%Xp=odqH+(TgWC#4m-ix(*$(;lx&J#MWg?<|7XHw8%U9G"
    b"LK~&D8zcNA@a^fkP0B7})(p>q^Xwf&=e0}i`GJ}W|YLkWz7LL}y0KcUQJ!qu8XTCNJIUo+9V"
    b"}_vAjJhY_`|H!d5*)KlkLqL_h5uRjip>h9?gqwOZUp)%A4Van*O0Gc0QLh#dakunNbF(c`G^"
    b"ocL?%+O`ij6Q0zXZ{zWLA<S{hk26%Bei=@D&s1I)V;Mlq6L@*6L&s~%GKnADo#5?b|u*-<??"
    b"p!G<8Tf5*LMP2QV>#tjUM^}y9WQ)Z;e99q{=VNR*H#ypWD-Rg>^^k7p9MD7{y&LKl1&c4=OL"
    b"}DGV0t5sOU`B!45u}GJOA~D1BF7q*1x$f?)uv(V3Oxt3~gXMnsb>CDW4(a2M<oOJDl3=!CR!"
    b"ED>J=TO5wQ?`vmH8%BeUMNOl6#BlxIQDO<W2X;~o~Wz;M27<*2L1_&DJNrL?`;HcQ^@h}rjM"
    b"u4;*E(kH?4)SGmJ!ru50vs;q5J+?|)^^M@+^B6054i_xa$z7=s+HmgylZ)EW$Z`kx0?4ubkL"
    b"W!(o`|1US%tCjoT%;8%xq{QQE=xG};S4avv6oqU=5|=0R>yur(so=-L+XY+}|3Dw`LE4=Jmd"
    b";@5w(qDjuNMny%fU=kUtFAfL{Ro1Mt!rVr^G|mD_^DtXs0%-!zxLQF23`PZV<0}LxZ8_!6Sp"
    b"8-oX=PpG!X3t`^U)5t`!NC^t1NCQ?(waD`dlFvckjSb1oNmlFZL~tcuikt%xAfkSK#YPF!%B"
    b"I=d$&Ik4=CQ=@f$Q{U{^gf3?8zPkzxQ%h^R7%){y{{U%0oMwh#S5A1tu@T()G9Ib<8DjZNMo"
    b"<0Es1q3L%?W?FI3?r&ytB~5c7l40nBn%dLx4%gcRY<^HRE+C1fr%>fUHxgw&Rof?RWnmiGfx"
    b"<A!{nVY!hmbFvDX(9<qWwoN%?feP2>Gzfq)QGc{MnVcH1#GxctgrCZPoQ$!@a!gMEw2-ezmM"
    b"wlZffDYO=>@<OZ}>5r+G2txnM63lv3--}Ft69??e%v@tL$KC90d<r>7SUlUmiF9I#n#gveVl"
    b"4WkQWfafIclbXd~GbdjZ}Lz;X5(UwUldUi7eQr@$=prG!+d9Nssipfj1~{QL|A$er`)1ZBT+"
    b"ea_RM%Q*US}*z5AH@`Pp5R;##~oiyoFz!!mhe)DzkCpRlZ*A)v>A!WLHJl<!bf}L}PfH-o$r"
    b"dC%S)v2Uc5I14w-1uFVoWsA}(_h|Pp2Hu&RqS7x6{$_Uz*o?6nqRByrnx$V8jgk+0c9d3YeU"
    b";O2yJOZ0hA6VX{Tt9drcs#^<j_xMgIHSgI53RRrg=7LA@dh<(4p-wni1ArYr*!K=D{F52KmW"
    b"p#GJD?f>m8HLYKpmupQS{XnhGeIefmaQNFUckmhQ?7S((DTQHB7K-1*qHU3BS~+H*3g>}<!`"
    b"cWPDP{(!zVpg{i`}52V`Vi#uq`xZ&sNR*S;z-5rQ(+*hHPQlIT6aC`NF-s0GCIL8Vzm0N{FD"
    b"mqtT|QF0^gWwuR#41WV47`NlCOs0i7{MP}&A`+y@|<X#7sWBkn6Pm{Nxk9GM|zm<RIktw!1f"
    b"NSVKTdq#=h$ZVckvZ#p2o=2dv*R~aD(sD^6b~4IuDAo#p@Eyi)JE;$x227YC95jS4r<Hmp$|"
    b"om#KqYhK-h~?n<B`IE)2L7U5eYX;3b=_o>)*KdU3`D=DgctPa5P*+n#n8Sp4Lm@A<msJuNX;"
    b"BlG{X=;iMnq+6Dy#z6KjI$8TS_a~Y0ZhST;xe{~*tconb`-k+6vqLqim+^EB<swU+ZVN9av?"
    b"GD*c6qVJw$2wFAOakYO(bYf#yU(T$rz;Xy<zdz-BN<^`_I%lhG6l4xOCZn>)gZLo-^A`gS#J"
    b"=%&fQt$Y|@;g(#CI=b4&|k&R{B^0GaNUu6c)>KodSf6+-TVy3FefD8s|JpAfNjR=cIFgr)>y"
    b"UiJOoeGOB?8p|wUi|diH3a4Ia#~kmnlx@NoD*uGZ)<Slat1cs!#~pEz=4WN*da`;rl&B!MIn"
    b"zcrIuoNct?O-As3e0^a}#mJbt9Y;^~{ceesX}6Vq3Zq_q~Um9(E&uG_dKx|vUQSGU6DYa^)P"
    b"Z!Ds-Yd>WHkOJ2tScv5jNWg-Z#0@@P>n2Bfk#Pjgp_y-un{ga#>K@0(uacbAqc1+oD&;3CpW"
    b"^Kghp^s#_2mp!@qYMO)8QGSKv(AnX)O~t5AMy+u*{K<55My$`5u*O;%T{u1S?~zb+D1JgP92"
    b"ekk^gv{uFv=-?gj~g!;}bMyF>{0a^PIsq>DOY6Wpt>&h-A`W0kLI8~VWutSM4G)--m7gvh?>"
    b"|UvY%)TK95f`e3xEl1b749T<qBD|LgubX~??`cOxG-&I5L<)dlWL|SDIEv^YOM4-^`H-RNSw"
    b"wV?d~FIGG1e{?-vo4#svx@*?F?|^-iN?u?Y>I&akn_5<&-C&~V?IcG)Z?zySUzDOSq@2*)7s"
    b"<2xJ&jg6ecdqv;*xxYj%UQIJxsKz-Slk*)?@`(gfN(LzWN|syhT}z0G`a2M%1Jf22q_9W6Jj"
    b"0Q&c*rX#Y}@7aY1B+6HW*i;<}SR7T4+0qZvY3k++B0&^NTt~KrV^fBO*nkhE-N>&h;bf4FrE"
    b"e|4XodOP`z#4sBQrS6TNs&aF)jMIH>fj`d`-^r1EjsJr{-=H`S__?WuT=^jG%edO_Y`Z9?bx"
    b"ex7uEGdkTeQ33L!dmek8<)!*v}!}XR*32q_n^<vRn*#3l-fJ6sGx~QlAyVhFdOOfO#lD@m^&"
    b"LVEm+(~00G_{mZk#$Xdi+gvBYQl0ssI200dcD"
)

if __name__ == "__main__":
    main()
