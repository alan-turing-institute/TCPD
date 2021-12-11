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

    values = [None if r[4].strip() == "" else float(r[4]) for r in rows]

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
b'{Wp48S^xk9=GL@E0stWa8~^|S5YJf5;HY5=5M2NuV0>CSok^Z9l0Z3mniJ8O|6hhwcDduj+&'
b'vull;AL5xdD_PU}EA2@+?aCP&NwU2*05BMYo)Nums=8n{IZU0otb~PWzj1YHF4?z6-sTQruv'
b'f^jq~2COuLLJ$Ed%j?lLno9TE+a!SS@xjwm(d<^`|rGouV{=58+vw@7(J~6G(%MZfTeek=55'
b'|w*kb#y|)!JM^ZJ^;bluq+z^(GKqvF$vzCshXFe#ONX^*|?hO`vLGalB4(NVgsoGBD)mvM!p'
b'V=mG9xMfx9R`%ZEX2tk_;;#y}d}H#8uF7OqbeCF-6hYC2&I@)Oxm{#=_NELrqW!;?1Ub+!PK'
b'!%?~oN@XE_woirKdm!%9+<V)j|M-V27%f1HV%GY@pshKXWPcW<ss)D-;rtRqXb=nU)XIL}=#'
b'7JIP_@y?it`&(M@=SU>zd~d;V}yTFS7p|f4#CX*-%Tu?wBp0NnW&*T#~!F$SRf^ORw*fH|hK'
b'mzue1dIY*Oh_>Hp;Z<&vvEuL$iD4?U`QKe;ZM@zFXbvQT50)^oal8gToHQ>_J<q3{jo$UMbD'
b'iZK63}%MvZR<{J+Q4dv^lccRv@u01<3Q!ua+eG`;0xkT{~)M9T(gKXhu7CyCVCRu<>|u6JW8'
b'5qmIN2(VKM}`%=D{_$%Ke49gt53wWOW^^d9@?DxUPt^MeaSHkgD5b>juzKl-2VM7p7<{Fs%)'
b'F5-pstVRmdS!R=v<N<<Ln*@|}<I{}6h13o)X=tz_6!`ian6qM!3WjDP!;>24diS5t5F<}$uL'
b'1?kqnE%Xi0re34jzcSmCqbdjVuYG4(@KhK+`5kFz5KQLIHx?SJf6RmHJ%M;<d-_opq>1NV4S'
b'xL?-=1WN))s-#^*)YlHGI`?nn_pQ{f7f<idE{@~bRgT5I~?qbGdfd)ZT-;D{}><)NHFofWfy'
b'QU@jRwcZeG%-%T1Ebq3A&u4G@7wtRz*PBsHdX;}q13~0npN_RP?pqgnvB#V#lH)B<y%h5V#&'
b'p<c(g2L8-%-XCPKmpTdWC+mL3sAg=`)Azuz*?3hsHyxFRHN)n&xB0mNZ-wv^|taTlA5WI3U|'
b'qRYt@YX4N@;5e}_vdhU34;a3y3x@K0GV17&g5<^@9daZdXT)mu8RPG&t$6g_9ZAA>4P@Vo|3'
b'|CUfRiKa=Ai%vs@<NeW!gKq?Hjf!AB|~JK0FW-UL<E&z7E}w>rj15h|g)tZ^4!P;xUW1UPGi'
b'RmMX6_QM9@H20E>q{2T_vlP{nwT}!sB7CVWK-L5lgAHl=r3?NeL%*R2d#EPW5<ZC0KxD6ZpT'
b'6{@0e;!7KX4=Y3%ux#JXkKK+EW_h9zpuKFvOcS)M<yW8GemXnzyX*fyOfeqM{=i^puC%ci^p'
b'5N;dqZcd@Qm>2<0JV0TqBrXcm>N)_nh_@uF*O4d_1X-ruErIjL~DVUz@Yaqb9<zs6iX+S<q{'
b'en!QLq-)V{i%)_OhgxYq?rxxiLMTw|@-|iVXNVXZmN!lM155no$XnC24E3BU0PN25?>Hk=9F'
b'Ea#CQ%FVCS7_+&fgt~V8oDcn)1;k+#%HbWM`knNpW|vJrBQd1SpzJh8yb9a;X4bJe0EEm3HG'
b'>`qq7xRo?D{2Qg7-A+@;}4*r3%OO9Qe-M|%(c3CuVgt<Q<=vAi|=-hs*!<B)%t7($iuuK=Y$'
b'4ut$z`~pfwCG$?E@X4`sBG{V=IMxqE9Y*>KrPA=4+p%cZK0cOBT5h?(zZoyS<k@5k>tq5L6G'
b'((Y5E8DY%|lK2+>l{y1t^#{m3yF0Y^JA&|1~BM%jg`LXlxU7}Be~T?g}uCJN1!*O%!PHTG|^'
b'`-;_Gp<z|JLXV=?{qj7kv1|g}oZeMELLxzu%cBYJDIcZ>-aW5j>Q8!GtSyYrhfpP{#KwjCKD'
b'QpFg~sAJLLKGy5)>Jh@W3)C0=)j522Na-v+rVHyiHvH#Hd7Gq&6ktnAZ)(3q3eT`(=^T<WOQ'
b'4p2j~4bD~}TDasDn{sJMs38AAooT^B*s(gj&bQAR3tH?ab8*%88p7cS_a?SfL>-7XJ{+HJi;'
b'(P(xhL(LBtE*uU5yd{Dd-P0GP?pU|v42Hy0LER?P`1?O+GG|~|N7p1pr4W_R<VDN0xj9Yy%v'
b'>^S)W>^D6U(67O?_Tyo|kES-sZ;BGPq05)`IN-p~r(4}sC(yiUmTaVXUUEX-^#Vc;3jH0^~('
b'kQ)~1;p@tXZw4h+E&Ko0-@*Ee*qy<P6*83bYhr;AV;^XH3lH_tMHEvg-NvMKB?@y3XM3JZT8'
b'9e``joTEFVh4pTv@~Nl_y5wxk=pa`?1Nm;5nqG$-J!CKp7a3gaL_>`b$Fxt`od<e_bP7{9;r'
b'Su~~x}W@9UDxo_a7pO1S3^eV&r%Xjc(olO0B5gg(?8QKA3I@@sY*gv9!!x*%Wfzj=JXkC>wj'
b'nTNPh)FRO)K;zb%tK3Em}F%o2H5s9M>$5E8CR&!-{eogBD8{>K8*Utr0AI`J9lNZ#STC#xHY'
b'?tj<SuhwAO-m+6C^BSQ`UZhN+e9NSV{P?jTeJ*<}jP>plzKW)|_wv1Aq`!-y3@*TnY|rR27%'
b'{fNGQ%OR?&cC5kI_q>aST&#v<yX?S}oWNTCP6T@Ou-jt;K`A?~2ISeh2l6fw>L<mnaSH^S7N'
b'F&{VVf8_o`)Xvh?76X0?^A4MfZQ9B0NWn%CFzBiASn*`u!I^%34(D_yaT!#i)US+8EGwqU;N'
b'DQ0IBd@!nOv1V*jhybl2+%?&d^)KUR2Ltr@~t_0`_hLUdI1_A<N5(f^y-Z^m45&8;LT;GR_p'
b'+P})WvuPe+47;W`h%i7jUMfNj~{(oDT4Qo4sV5}pKDtRg_3X}S2>rn!Ax~gSJb+NUfaI;fZH'
b'<fXBFX<Z8LjlGw77$_UO2_gy@1<X(6^Gp0Z+s6e9t>Yjf}qRqdK@vKI%BQlNPhmhteKkE-X1'
b'-f(y*nu}=<r%H0GKzAWsL4T3*e=>PlOl0LZ9+G2z@O$YvB%zxk`xbFF2kWT?%rBnV*<)l?nJ'
b'Q3?Ya2U)W_XwnIHV=D7SMrgsDcd8=3|EhMzwvspn`>7%I($uDy-^y-|;9Mp^3;sJ_i)$oSN@'
b'O$jvy_t+gPa9u3F}&KUo1_s!Z7wZ7!!1BY*yjYWMbpUHZRK1wptr8v(ZV9BoY>1CN&4OI3Zj'
b'TABt1M^ees3H-B`z-exv{AC+KY9x-#o!*|ZHV573*e~-bSh}Os<M%2qxC>i8Ag`N{wa80EfN'
b'423DsM<DC!X1i5w67-ZmL}ZAlUb$`fuN`ZYxO2^{qhhZ1o&a#jQrAsFAW2Pf0m2FRymh{`w*'
b'%6V@M<Y+zpEiZm7zuRm85(Ibom3}X$00FEN;?M#B3+f{KvBYQl0ssI200dcD'
)

if __name__ == "__main__":
    main()
