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
    b"{Wp48S^xk9=GL@E0stWa8~^|S5YJf5;l>FjfL#C}V0>CQf9xZJdRVi#unUxyg)hdj6P4u(;I"
    b")!-Mi!qJ01whccsu&tdyd$@ca*B#H~BwDQTv;0-gg6iA>7sidD`>Bj7YNlL>_*cP$1g5_cGi"
    b"%q$FisPGBZ(Hf!B+7whhwtP+9`;a!w?f&$)~612zuEmVhhH9<S&YxfvTOwKx-I1-%OtsH%1d"
    b"X>(OZ0&)AGm?9Z5@(3>Z5J>&`>Hd-mfG@{C+Qrj?-x8>HBd0K^n0aef!Zx_X!KwHV_;ETFEr"
    b"B(D~dA{@Z0*VJ;O@I-yv)Do*q1cNx}LN+nw)%1<8A=5Of?d{|{bIA@7gllsFj^j=+#3_uY2M"
    b"sF&(I`Vil_Gp)1hzIJr(ASuG5VEnd9bTO(7)JQ6S;PZ5!m`SK08!$#bu|nWXAB1`n$WUDd4+"
    b"0;mLnl9KM@t{Cs|bef3%hdauMSy~<HkK|>;($Do4Plth$twMS~pR%D&nM7B!5ZTj`DQF)B?*"
    b"kbVW>dCGQt1Ayg}WlPyp{`<~9ROdtY9gnsv~dxd{QdG0*4lEckXnev*o>&RNxWpMS^0jMEN$"
    b"f+f!55va>EZ2koZh|xzfn3`8cwnWx!lBFD4@E8kpC>K4(xvZ0s3z&yF_PFWwRQy_!1xSG{a#"
    b")mJT$|hsgiMZX6rSZR6dP~Xsrn7%R;&T_!dw9_(){103F2os|r6rmw?TE*8s}Rl@!WkGX?hU"
    b"u+73>9Dnc5vJktkV6Cz^!q%&x8a2Aj;0OfTm4$0jhMZXt;Kxa&k9pu)!d6KfN^EI3^h5r&h<"
    b"nxs3CVJ6X{`4M`_di<Xe?a{Q<YShWuQ_*%CU7BvbW;u>^`s{?oVbb5vB?>QDTf+lhXjmi3NQ"
    b"cGpqcAk%knL8FB>DmOczB9=sw>^yR;}9eyhcK&G_h558-|+;A=jAppiZ`}U<tS<Tk_!EelL@"
    b"%bFkmRb25cq+8pKE5DVbP%f_01lv(%dxY9-oCY7?gWOo3}p>q7A<-wrWHPx#g81C$(e$`h_&"
    b"M;)=xFxrmjXQIatl`{;hXs2qQB5Iw3*rPSn-7K{9p{FX6E&Y7iQcmoK#O6?SSc<~do@E<Uc2"
    b">Wtoi4T+l5MBh&h{7|BFNAFUYwYXVqT1p0Foj|wqn-XPWYOO-bS40Oyqo$12)OSVw-3z^*5k"
    b")!U!h8ar@`S~;mW<h8JNb7QPe8-4cHsrC=-A)5j&Hf-!lIw!P1*y|+UKBYB#wsdxt5H7Uk(x"
    b"=o#^*kf_+!Kg9uF{QE9676}jns1`ho9eRDhL0J(ZJcpBAtph2K&Q66h)fVI5gM)MNKLQ#vO;"
    b"BfbbcM%LD`x$Gam|Qv!Gr{jrtNW?Su*_?rUd{~l3|WkFMcZwX;!Rkzg^q$2<rX98)$jOO(a~"
    b"<&1AHzF%NlOr1MJqtMhq-i0@l0Q%u|>#F0?)jX0A@S)Ei;n$CkSiRin<>Mm^XzkyhF)qy{(m"
    b"M+hV4t$%0AC>0&_C2Pq~;mc=iI#h~B_<lg8LgZ|>nV&@F<UJaNt5LQhSmN`JtgkkytiF(U2h"
    b"?!qo;CIfn(V+Vb}n~I9xt84nq0~=wcNhUA0gE0cwK28akg>W+wbHnC;h82x>^o2#SVu{u*(_"
    b"{6~LfRaL7X0>3-vUJhv1>7{}q%LNlRk9gt-rj$EJds%GZs2L0Q?(R3U!VCkxhlTBNVQwvGOY"
    b"0mo!RCKvWA^P;07~$@+V1&EUpm5wtJxojY#@ganrXBnA%qUn>*4e1Wpu80vBjs=}Bye>!tQy"
    b"up;&9?qi#)TIJz8Cu`sm4n2^u470I0TxF4<aHiiW=gHG;izwrh7JUOEe$c$Mjjy6tvF2}E~l"
    b"7+!(J1YXh%Jv}BpA8@qmf5d>7Q$qOeZ@)%?gy_^A6c2}>8%HH)+c0qM3P2Wmo4_x_G-UJun&"
    b"<xzTy*|JnSF{e+O4uWRrlca7A!#F!N|cqhrj@0-?vxbXD$Egp=8jX12)+OVI1~Hz#TKH-BC{"
    b"HM=t*NC5N|AuGC;73wv0&xvkpI1UbEn7K!LVZJ7goa|BhiS1aV6eh%oFA_2til)ljReJxly4"
    b"wERL{@Dhoe7CbFAOoxD4>N%F*j<)99H8HS$lA8XG}ItOJ)#627C3x@jc8o8k)T|MLEL+HMfT"
    b"O>M1Ij^$04bpslzR2j4eV=_3*~)FE9D-NP*lsoBl$S2SQ#oU8tF3uv3**kdYt~&PJNdEb=3$"
    b"@$K!^e_}~4#iWh%Rsr97Aa>OxMnB>T42K{cEOKFR%yu=!d~;&+vT$!SdY(i?g7E$qy76jBFH"
    b"o;G(aTPmvdrUo9g}<?dcE+l@%O%mB9EEucFG1vnc{m!$nR|Cwd~Nj%o!8yc|pTRd`u=^=Fyz"
    b"A@Vk503n<16n148-4O-<BtJCdu=3J-xA&}KO0aaO$H-97w3ek}>cr8YQdto8n{2H_D+&nCf)"
    b"atW%fd7W=lGY~=ehg>Brq}ctNy9syqSQr`7i3?ICRM%RXrlIl;z3%@J8}~e*Be?Xw<`v+6N`"
    b"68*yLITwM|pWoM|M}mRt{aM(Y!(c#fs#EUZnLF48J$P@<Qo9f-D!c>7uF9<@ST7%N~c0<EW{"
    b"doUy#xDydt)5HnZX9;pTiO((KicFg;hfCZgTbn}s2cgv211OS6+*s-oGLgyqMI}JSJK~p6$-"
    b"nKI$3^gmAX!b{<H)+ylll*kdhfC;*6~n8q-zACSB9NzpxIi}c#tPj4p5^RB30|+`2~+|y7(z"
    b"hE-2|PZXFZE^IUfqZ^xm|h)6tAo`73KZ}e9t1+y|zj}5tZUMnb^cKswu;{TWL8+UplIcinO4"
    b"uw=ovYV!GDhC)5vBr5F*@Odme*2Sa+*(6Fj#PKQITWiV{KIQs!H#^95bnnRq{%mR7xFctahi"
    b"RI<)~vWpuj`4gI_!INfI->8OrT;S<4Aye8zUR(1VGzzb2ROr$uSKPZ!P1`Ah`^K}A*QN!GF9"
    b")`-$EW8M18v08WJ`oOt3RUVXCQar?!FUgNSp)G4Z0d+V&<Ddr<TRp)cw*A*9xFcDFe?r(PB$"
    b"=asLA0%@RZ)h1Y0xARLnavT)LABBPG-ht)uI6uE4?z+dZKiJWfqJ0)e~ugf#|C?3Y6~F0}@t"
    b"{xEqoXsQ_r{#aLK{7-7BX00_{~(_?&fcsC*RDKIvfb;<$!AvEpn`Qa&wC}zcMXECxsl0Ttx5"
    b"i;U<x+)FDbgF{T_<74Ye;90i5^iz4M&?Tu-sy~f(PCm)!~p{`#>KE5C-Ut1K#T&Od{V!Jj()"
    b"o_PS7Nh!Ov}%z^&O2K(Gl_zV6lDP3qpU5ua4Xm0ji@pZmbSX;_tg>W8#BB|=Yss67zHck@57"
    b"S=@Qjf2pqOStsx+9h+<`S#=%43T^ia#{B~Yx~`#z=h2CjCss3h0iD!Cv6^C_Re=9}1ci|j1e"
    b"%L|*=;;rr!{GG8ct!KOhSeG6^D9a$GAS_lBSU3o=wSxkCTah0BwI4#=F3d1{*P6Dn^rFWAW@"
    b"f+HoGNpU~vP8YmK@xYyQUA-`#VNi`U)_1?Ijxa{54h2;G6HYif)lSSMkPPcZeGzm68L`-GWx"
    b"kY>Tr38EaH*5~Y>zw(4iaYq(I=5%-^H505>e_V!)IMEeLbC^mlQ5^%RL?=YnzN(qI@1u$wC%"
    b"n0>n5(pm0DIB#PjKSVpSh9^3-HcJD$LDUB|NyW2a3ubm+%}%;7m#8tO*l@{wHh5zs~&YvksC"
    b"L$7XoJ{i2BrZ9!nsie*q6WW<k5>Qhh-dqTJ{1B?n&u@I8dZmE>@DJPVBOLU79W`TS!yimNFi"
    b"r!ttImZZq20R@56ty6+2QDm?EyVTU+IaWxo409k%3s|?(iY2=raEZ8rJ>Zv;QCiS}gaebUAE"
    b"byCSAYpS-ZC&u^)uw~)SZvx9D7Dlg<XaMkFhE7z)FNb%(13d$s)1dJQ{duH)1Dcc@MUu<y^E"
    b"SNbN=Iq2LD-su_B<B9=mhN{w>nZU6;l2pNP@SQG*W)`Z!uglE<|e=?+9SIYA&8i?vM@LVkk!"
    b"sfbEB(7btzBAR*DPyr}1l2QQK)%R(Efg12?;}<CJJaliH>@*J{Y{oeXEgB8pj7Pl}Nsj?mpC"
    b"PCK#wOV^Eu0qpHB7L_0wAA1sozUxTd9iLAy-2tK3FUB7qc9rSsS5+nGkfsBO;AB6LBkXy)mB"
    b"wUxG}^O#n=V&0pUaVBt-dBfceklP5QZ6dB;b1Jr)tg$@j>gQ3<wz<@wXr9Y>ibC41Z!Dl!SW"
    b"ePA5WFwKcRsISIz&+iY!Q^~o>|RQiP_K%=*TbI1N^z<|2H@6y!zI<ry7!O$6b<vIDYYEU6i2"
    b"2uOK?^!$_R9Me~l$wouJZ`<3?A}Y~^P2gCBz<Xh=+{G!)E@8M!?>AK7MyUB7*_q_N-P|dt!@"
    b"i=<sc|js-~2x)2^t0&t9~8SE7jpFHaCklZ71(?uEsITKELh#>mnnn4kjSn3k{_bZ7(_GHi0q"
    b"XYe;P$krl#Fg%=DAv1cbczG$}M2tv8>YOB)X<Os$!hRo%{X<K?G^t{-3EfZREy_is)q?Imof"
    b"Lj6gs8L4U4Z{r*&%6x<+wK@+v1~CYOt}U$o|U>eL;4l`&#R5OtMFp56IDCor=M9e64ltTK%U"
    b"W#F8xK+2=TZsNC?uBMkOrJCmU(DiYh1vcx(|NRPLA;!zD@hFJbom>2l#r{s1u?+e)<51J(CB"
    b"=2jMBq4i`lo`qJt<Yb_|B`}p1hfHyN8J+56aY2K9;1>XJS7ZmAWyldKF<a#3*I&S;O93il1s"
    b"2xYb2PgpkDDY0u~yVoXTarfglRQL=r**l~$S=h5`p+QRt*b#LolU*28t^{|zUHcI0WI$>BD)"
    b"`nvJDv{>ZilPN?fm|kSh1Nf)M2#e;51wMJ)Gq~-sM!L6^>DcG*b%jMc))fWML#Q?x$B|R0@0"
    b"$Mz*8TSVf3GY*p-1D8o=#kPq=@WNg+(P4esyubs}r#IX8^O|EnH?oM6aVbD5QnBulK|t>@B7"
    b"MRBqnBCHAGfU09+QsHNKS`0@GdK$A9VZ}B*e-@)ML#lyJT_6P};_=_%7z?NDfE0GP$8?+RW1"
    b"6Gi)UXX075z{thDQ27ni@^F67*aIhpK)5Qjw64kw4LJcZI21FYX`vf$h2l}2DR}&ETu=wJ#f"
    b"fl7~j*g%aKtu(r?kNzN`nv=#&S{w!(q5Y0x^PQ9JWwd&l?oFK>%=G|&%+>0Tl<vvUytO5_o9"
    b"1Z&j~yh<bLY}D<K<s7|+S%Yh62aQh=Tf`Ku`MK~u?Xr^%QDo*VW>sQmA{%mKvFvzZvw@|>aK"
    b"$x{Bcr!0DiCtXO`TXt;n-x>KKE6*a{@+O-n&L{cmA>Q;jEKP5fAXT_kc>}tyA5cK#LG_1ZXq"
    b"Nf@@6?&I|kuUv@6VLbnvB%t948idVXNO=clk=0C;}n$@cg!-Mi=LKWiVs7$fhg8549oii|9z"
    b")qWqfv<#T7-PVliyYq47>F=Aex0ErYoqS0h&+^|$x;h573tUv-%+)&RcB|dHkJ%~OVgiGW{h"
    b"rQ*{>1CVO*4&<OVcgSBF;y8Vkqya{p^~?RkyRBO_DBZe?*E4yH*#74}OjRMOiAEXc3AhCv>S"
    b"wC~&#Z_f+1B;S#293)Ivdm*JGk@eob6_DUe4~9alg8FJOWGf(SAT5~A2;YC<Q@GMzt)DfIXM"
    b"c~lmEAAt*eDylJg%@`iI@6I-3d;c-Xlo&@A^zjaU5isEPlC#ndCK}HFs67g1Tf|wNr)4AQS)"
    b"nivY5=xoQ@8**$k;fEgSnPEKdIT%*we#)=-*gz|(si&AGmiCFN$$hW7X#N>On@~CeVD>c`no"
    b"C^@Tjo>aYMb)q<efliDVH8muol}0Eqj$#QR;;n`>T+V#+%sEVT3JD}g}X6}FN&aT7?ph7&B`"
    b"nj9GHj*M@ho1-qophD5S4q2TKrrc5JtH0N077Z-Vm0C#2hm`)L3Yb3)DBsn+lkQ!&Hk=W^s;"
    b"aDn)N^DaP@Mn&bRD=ic14ba7oJ-}H^As+U%7@<LUingw+*zsN;p|jV!@c-Qv@`)s^S_C0Q*6"
    b"FgT&O=VF<){sOGN|gAXg16C0Aon(po>a&S*SBvg{z{=Sy48!Bzb!PGalm!Tt!K(BNxr<C@0l"
    b"Z$ozya9o5W$6)w3ysl|nU>V2eE&UK7oCUsE&?hT=ZxmTe?(LvABZXzilVN@SnZ?ROFf0mdWq"
    b"|%tdoXV)_9m$Gwbgn-C@Rhb1aQh-F?*Ev(BVE20vlVodd7mt`4@@~reDCMOXlIemofc=V9M_"
    b"xFeD%8%tQBh(X?<zM7VJh4zY2QE9|hTqjsIRLnGt~1#b~^HVvdN4t0!xHNS8q2^=7X}5G%Yp"
    b"F&g=CJwGua-on}sQ!2=DS8=4_;Q8z5YAw}@)g!EwXwfkc{W7Ezil!ax_!|Is2bh)v)5=CzBy"
    b"L*#i(~PlDmuyZ61x*t)FZ9);SC$r`P&)nh}j~j1i>_sMtK}ATo#q3U?;8r=aR&EHK;ifA(I0"
    b"fK%pRiGD}$@h3qTA-_DZ2@rN1D5*a2mlA0cnGJ6m*oWbj^V_Dfz(!Wp$qgm!COOEzWk@t0;U"
    b"b9VEw6fz$o8RZK+L<jRY(%)zSF{5s5xyR*O2w86F6g4Gv3}D&%=@UKNKEMu<X)PCJ@#5&?*7"
    b"m-$KN0Lnc?)whh^;p>Zy|VrX7Ny01ThEIvn(bPnu%C6RAF};zpL!jjTqSOuUN9<Ed_tTUztP"
    b"PJhy(|MRg(G4rZC%I>T3lk0E3cLLf<wsHglm)|?E@u}^Q&{nqn8r19ZH=h4k)sv{4F$W;LCf"
    b"?r^q-{t2DU3I>ldGF{NwDoX@0{-nK3dnHA?B<u;(aazqCkHX9<FwR#a22xn!IZX2)0@b{@x>"
    b"sAscQwt`s{3&L0s3!ZSwZq_uT0jo`RjoA%2Wp5!hzbRElju5xQ=JC&B{^@Z3{LLa;`b!{TDp"
    b"-9i`9dWd{K0CQI#*)<Jr80Xl-&RUvDIawnH#1fV&3Sj*n8?8SLU^J#t0G5=_sGl`LPe_zx&w"
    b"<&oo_;>7p$NBpG0dP=bt<!!P0E*u)lpytW==jDXRin8qtG(w46IcErVPRPs&mn@uQ;ih3n~N"
    b"N@~8|<Yt|n%QfY#8+Q&t1o-~rTNmUvo!?slrmDnmvZq!)sVE}Z)8x7OMf>(L4%~Ee64YC`X$"
    b"j67O`}3r7Rik)x}y3dH2gN^PI+qZAwseDI<7GIBsT)4;2e@ih|d{ypMD`*{i7appJ(_=+NOQ"
    b"Oso5(&`A}#K!joHq-S}ApFN=;$hdr4EM<mYXJ!^015CyU1*fZZ5Us@(+M)f)&g$I9x`AeVSg"
    b"iNjgP5l#o2-y`DC{f@u)<xk(e>QX9YXkLi`E^5*dIw0p^cZ?ENfGme>>wqA;<F#Y;<9lZva!"
    b"$X8;bCEI>Uh)etHlhSbbK}bbPgMa1!z6vT!(+>=iG|*{zR~*wV?^s1eFHO!AC!(Yx=0ee8jH"
    b"!t#u?J40$jJRL!})OJFjVjwL)bJYMF8prci`xHL>`Cl>Aa0!jG$^C^K@wt4lu9Yw8BmxZT1a"
    b"0anSi^~ucES=I7I7{)!Mph)-aFKL6NGJ6`lHqYA=r|CuyXc#S%zWg5$x=_LgHRSQl2QF%YZX"
    b"}4L_tq+bPWYwPUR-#Bsb}t2`nYJW*waLNOa!3g3@A0~3e6P*@S<0$7Uoha_v<>eQAIy4KV6j"
    b"|>DlKm=GZjZ6CqrD<-OY`5pV@;m@jlJ4cLqmUp0YMj&2+46PBB7jl{ETp1-7?dk}8(fg!z{G"
    b"*@4-*RpM|@B0mb0*rK>m+d*?Gp>iyXn_0-d+8fDsKg@x4r8iDSor({=PS$bn}s@6h!CYc9@c"
    b")7K1(1<M=|UU0`3XId7+44upx9(D;nxy?iqCLWkO=-*_ws}PVG^mEu);~SNe_8wXz*TPpVq3"
    b"1=t)cz&sYieTj^R?YBvle0UMTHzu%7u-109arQspavAxWiGtq+Yup6j~#B$%d<%WH&PzJ3;n"
    b"u8i#Y!nLb0Xk6EV;bw}BYG|(q3cwkCL{>$8p56|WBp!QpeZ5?oI!+*7@gO=IZP1p@auN@cZC"
    b"kbDOY0kwMejOj6*!%yDp>13y)jrxjdId|qkkj8Spu}i`Ry;Cqr%l7claWNu7hA3s3?abRrv#"
    b"#|lBE$YHkxxD1+~FD^QPb(n2N0S{E^@<=K{~r_Sx5JYEK7dV;^zN;wKpQ&GnlFMdRwioVJ^x"
    b"dOhW!LlcKB(=J8I1$r0&;B3I2MfP6RBk)sGx-xX4Vj!@JmloX@{h7c0B4C1qRG;eHX6~FD_1"
    b"xW%C1wifjcxCXWxpl;X&}%O<+Nh-36pN2T%CT*gqnH~xS=;`jrm_OT#Tb=14yGO_NJ}0UDtC"
    b"GJ|W^M^{D26EziOh!lF^t#b!sBnyv0R#CrrD!zIg#NG(1vO<-bNK6ySOK#QR9<L43N;;m19;"
    b"aw|Em(#~x`m!KP6B*vU*P7=@fS~BVsT7qE!yS`<!^cI+u^vCs_GwwpfkLvl9#BJQN>sHT-9_"
    b"ONa^BAB?%x8hoJ;2%i&o|TSedt2CYXZsCNNigiG!PrWS&f(=1hFP#|K^N|7mM<fbOZY`B(!-"
    b"OIyi2TW38B&MaJ#`kN1n+rMtUURlkWuh7Px-m_OOwM|a`G1hhkkb@{{_Bb<S7&qA4*zm045J"
    b"@!sL_baH7by=MQLV8$3?w*q(wa}jPD++RQaP9y*i&|x9@arhDmzjL?mDKDWc%+u<D@`(zLnO"
    b"oA+_3JZ#AssF5C*~VlLP&HxBz}0@A4T67HMbd(5PJFxyqtv60~(?5_2-?UE3N7Udm6SAk!1e"
    b"KBjN6@TFS)2KE~*X#;V?%&XC&=sy=zskCVQ>GJ+bjMu5Jf;Hz-){lPXsgfU)&RNvOkeL%V=l"
    b"+&ylba+pThz^A|puhZCv4FZX|AP#OpyB<~9UCPlRVFuv?21_fQ&l!qmkktp$4`DjG#Ad;7M-"
    b"*cJ#~{GQq+T2w^vb0d{ca@|H`0k-<GB;v_lG54#i0<p9wa4%Fgh!O4Q+A4R@`~!}tp=w7{{|"
    b"M?me_|{oJ-uwAgp!tgd(hhRk|!E=4Y$rX3J)C{(&XHEGVg(m#i1Q#yGs=BPlO=ksi@9pu?RH"
    b"AEx&1Gk3(k&F-410pCI043dqsp)zUHxMK;C#17%vLcdVdQL3+K1czlMmzzvS<Lys6&u(8R+A"
    b"J3=t+{N^7wu6C|C4E0uWsSZ+PH<@;G#j)Jwp)$pWz!;T?7T=+FS}#Pkn?@?EKKBgvy5d`5nE"
    b"kDv0jG7wWTjy7z^H7N#zebFZ{kaNjna39C=Eh!?|S0<7t1mB{P3noFOq?iQ<r~cUXM+#k0l9"
    b"$WgeU<pw9x#RiRsB2S*Cl`Xyy@=h#zVnNVwGXxF;=BhfGRZMi<ELXx4Jt8eLq+0$n2kB(~e+"
    b"o~Ewy1^FRKuE@HE>vh0DjhYx4A-rpEY@|ds1vXr;zn*x-f?cN78sJS*pAAc%)R(A|X<eabEy"
    b"-DYH>kVk@7xQ?aA2sCJOMkT>6$t3oS9mk#8jtpJUEWwLC&V2w{8)Pn;7ZF>ZjR6HK;;z|2^{"
    b">%9ChAjSD9xX|R-^p@RhRV5Q8WA_mS;6%LbWM=n21cc^c<CmfH(3f8p2tvbONet<mL(UK-7*"
    b"OqAm(9u1H~qzl6cC<^p5m2FITfp5O6g<^a5@E4CDnVmgLxJxvfU_e2$%V=l}YJ0gA_s5A(1u"
    b"*OWwso2+g1Z`tiA@QgG%f!|l{-rlS*$kEdmv@nS6IfXJb2vr&ezXK<!A5;<=oyt|-Q|vK*0L"
    b"k;pG|Yf${yw`=mvYY2T-z<kQj%cjKZLXpoRbCFAbx)Zq%O&xAX#0XJxwMdI(PSFpMkH9-_v9"
    b"szA5Kv%*^{t?UJrkA{@)ILG>40+&3~$`*#4AoZeq-Yt)r)Q?l1gV#e^B&NU?LaNX7UOzL>y#"
    b"!rp02=6ia11T37o!WuJ^0+1Ok{qYEryhbR{yONrlTux+QQ-Bo=EB+d2qDbqhPa8=^{c29+b3"
    b"QuM}#2L%263BC;7e14ODhf!}B0qWGHHUu+1(VTupFaBgrYzl^+^KXmyzIOVB^7-9<{K+Uq73"
    b"yOj*fMu48EV`VE&Ghz~OnW2f*pTL^IFg4fR*4g6ok<p)mGEu5}sXSj3#4Fc?b;Q>TAdTN4xl"
    b"CuW+ZWmL7om^lb*CDPvA|R10XukgjWFIeodYvz*c$j!T)+VdBmBkTTFYX_veQF~T93$6c^d6"
    b"f9ppi67R{CS9UZg(u9Zz}%+cVYK6WSNB@+j`oVUa>zJaXGh-a;sGSv}K&ald<Le~u81QIQX0"
    b"5O6xhU>N>SEkMm0E{*fHrQ;D$3J6v=c(fbk3H<znan6;tiT)wst>Tr*EKTbt91i-w>>w|h7b"
    b"T)_u->Z=OqEiARiYmP5!CO;|T8c2y#-42Aa&V9Mwf&{3in%gRGXhx+m!psvq@m2e>mzkhjz;"
    b"O7(f44cZ0PVn6g%xYXRAK|rC$O^w?gkQjfZj~$Bv5|jYv?!EnknB}nK?)78sm@ZEq>cb#Q8%"
    b"nEKJ5k;(Oyh(N$eKdu++*~EUtd_rPTWzfBe>b*@Z~c<ctj7O@nWkj9JMPS4FMM&c|zzOVM%M"
    b"ILk|r%MxY7^d-_87F?aos#_<tk)pUn)Zf=b4LErJt5nJx>p2~qM(p1jN?C;*EEkLOmF-zLCd"
    b"`@p>-ra5*_Wh^`z1y=0T%F@lB!K*Pwig&Kt8<2Bnl=3W(G3W$()cN_mh-_!!Apn4Y{kSgU3x"
    b"n}@uaSmkM~^Cb`dM%vLLuVi_DgckF3H%{{_;u8v%Aq%gOA3=FGxl{O`0bg6CpK;Q+4X{>UG}"
    b"3;WcG3gF5n23L3-55yfin?tEUR+*Vq9HZ_5oXK&#Tb4udyLCZ4z+XMK${Mq{_+cOO`Q#7yOB"
    b"LQRvzB*YcMQTt(>3yI(a`c!NT~~qI{p_ET7XuCI8MXYdl5nkzh1D(qx1)LC?YO}KZ>2%T6|!"
    b"Um-0J9sLpD*5_H+<AoQja+k{rv4Uh${ZbGUs7GQnUjm6p-x57`E7HG3u)m~(`<-iz&G2`O;1"
    b"fNCdeYng_gSV+~kjG*cBekWkE>=&Cj%^DFE=;ItMW0EKX0>^Kw@M;6Xn4r4Y<8W5IFW$kDu}"
    b"cOzr?{?<9-S}4>z|$>u8i1>-38dzPqUw{vOenHRatmr`~uMzxnKJ?W<jJB2YR_mK8xpJrjjO"
    b"-x$nt!DR{(1FdkRLUv$0ar}O;4=4I{N`lu>uoh;}fCG@PG~rYyJvxfj*^iw4s_6^?N)8r7Qb"
    b"V5%NF^(K2}Vb9=x2mi_rxmbY#4H=-4eMo(B}_<DwMI9sj_D>4K3>uEFoH3_&M|Qr4053;fvA"
    b"aGEkS2ae5v&KjF*6$1nFFD04`K4u7dC>{>vn{bdT{Q0PK!nJ@k1s?Ya-5K(ewF-pjmXOqv*m"
    b"X(Nct#9566EJ8Kpp)gRY~&RC{RC|V5^G3bZce14)UsAdJ^mo*_fOc6deSFt67*kvh}^(5>xB"
    b"`5^J`k(4(f2!_r&N)uQBKCVS%&`7U^TWry!6M6ZQW!e`~-O-czFj1xuJZj4Zo3eL~A2bASmr"
    b"7J;&PTKduZc<Sn@AS~!*SdNti3Q$G?!pLQH_(})lTN^lKY6HHwa~(f-BK`^&AOdjOVvv#@rq"
    b"K4?W5pCK3b6pK9mS7JpbiV4*#lR;o$j?FvV#fsGkum^d}Otr-WKEF_Hi3)Z)?gz^=X#as4f0"
    b"Z2Oha+Q!6H@4a8OrujlWMNVWKBGCpmO_Y2lZy;YaP(4Dw82x)(LQIh{Am1Z!^2)QD?tgPRMo"
    b"FNfiSUqmv8H(giwavmU(;nYBid!1T<e=T(2f+W|D%3ofKdU}i5tAM2EN0y?44OrL<w;voSX6"
    b"|CDNDzZejR?F@dqzXaR|(>K!n<)CYi|jjXQI;y$aTDR^a7~1|>fkBzb-8+-*d?$enGo|85lH"
    b"*?OL3?!iF(sH+LLQvYzlo%`zMp7Et9)hOE8&D7UlhnJI;{grRNv>jBSrGNC4BLe0@qcstJSP"
    b"k@2ixgi$Fx=1Pb{QxG>x}57EffSX2h%@(Edr(=dieZY$BQ~3feGfub{P?K3@1PQjITn3XIUa"
    b";l;By#uvC+RG6QndwEwBQ<ZA4p?1OtBHs;c_@gK=`X!ZcOe?o_D3nnkGXZmo=OJ0t>Zfoniv"
    b"TGs79N^|RjeNkR`2|QcmuvLCG;tkheT;NF{Tn4;$SZN=en68ckLn<|^GFU(;R<m7VNX~0BpF"
    b"GtKJh&{7{0?@*tmK8?PPSEmVN8*-5>++-*SQg9W<b+AzB^pJ}YusmdmKtnM=AM8GQ{b1c8R?"
    b"tiul3#LKL<;tj7c6xR@b;V*I2Rn(RXqKDfP3TqZ3>|-C}jNU{K7EQ6xvcB$i012U--<FyziU"
    b"PQ=^C2q^v!{^xZ2}TKiRqY$0CLar3DIanr|ozHvIpNs^=Q^u8F$i0mSPeh*paicW*4yb?_6e"
    b"%Um^8?bJR}acg16K8)m9I+)##&@8iKRfTu#IgWXif2#os@u$P#3IbvkuB?wj*>${%IO-C1<!"
    b"l7|p_D{K@Xf`$Y!w}91NJ;0kdTMMGK&6j{T*0o0LETzr6$1&OAgs2ftrqcE>-R8xxr%E$gaX"
    b"{Ke&33{<+iTVAD|-4NA_^-$8FAD5!f14H2ID##6wsZ*Zk=$xC(gK%FWMrY^@$_#U5$ML|hUe"
    b"h=1x7OHr?D-xpYiyhbj{$?+1otkS3I$T}2C=RKYYCa_I8&rXw_J&B=i>Kg_3M?^-UR{81XfE"
    b"s6Il@*?@l+DPiFte11Q;ct$yhb3UOK$KBv3*8cJo@E`8AbpA105Y6WA)>G00Ep$ii`&UVZ0b"
    b"DvBYQl0ssI200dcD"
)

if __name__ == "__main__":
    main()
