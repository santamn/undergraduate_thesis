#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卒論用グラフのための前処理スクリプト（標準ライブラリのみ・numpy不要）。

experiments_p-60l/ 以下の summary.json / trials.csv / angle_hist.csv を読み、
pgfplots からそのまま `table` で読める tidy な .dat ファイルを analysis/data/ に出力する。

出力するもの:
  transport_m{m}.dat   : delta ごとに v, D_eff, mu, T1 と統計誤差を beta 別の列で並べたもの
  pphi_wide_m{m}_b{b}.dat   : 広い断面 (x~0.195) での配向分布 P(phi)（delta 別の列）
  pphi_narrow_m{m}_b{b}.dat : 最狭窄部 (x~0.815) での配向分布 P(phi)（delta 別の列）
  collapse.dat         : 全 48 combo の (<|sin phi|>, v) 散布（配向→輸送の対応を見る）
  heat_m{m}.dat        : v(beta, delta) のヒートマップ用 (matrix plot / surf)
  channel.dat          : 壁形状 y = +-omega(x)
  meta.txt             : 幾何量などのメモ

使い方:
  python3 analysis/prepare_data.py
"""

import csv
import glob
import json
import math
import os
import random
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "experiments_p-60l")
OUT = os.path.join(ROOT, "analysis", "data")
os.makedirs(OUT, exist_ok=True)

random.seed(12345)

# --- 走査したパラメータ（フォルダ名に合わせる） ---------------------------------
BETAS = [0.5, 1.0, 2.0, 3.0]
DELTAS = [("0.333333", 1.0 / 3.0), ("1", 1.0), ("2", 2.0),
          ("3", 3.0), ("5", 5.0), ("10", 10.0)]
MS = [3, 6]
L = 1.0  # 無次元化されたチャネル周期


# --- チャネル幾何 ---------------------------------------------------------------
def omega(x):
    return math.sin(2 * math.pi * x) + 0.25 * math.sin(4 * math.pi * x) + 1.12


def channel_extrema():
    xs = [i / 200000.0 for i in range(200001)]
    w = [omega(x) for x in xs]
    imin = min(range(len(xs)), key=lambda i: w[i])
    imax = max(range(len(xs)), key=lambda i: w[i])
    return (xs[imin], w[imin]), (xs[imax], w[imax])


# --- summary.json / trials.csv の読み込み ---------------------------------------
def combo_name(m, beta, delta_str):
    b = ("%g" % beta)          # 0.5, 1, 2, 3
    return "m%d_f10_beta%s_delta%s" % (m, b, delta_str)


def load_summary(combo):
    with open(os.path.join(EXP, combo, "summary.json")) as fh:
        return json.load(fh)


def load_times(combo):
    """trials.csv から初通過時間 T のリストを返す（status==ok のみ）。"""
    ts = []
    path = os.path.join(EXP, combo, "trials.csv")
    with open(path) as fh:
        r = csv.DictReader(fh)
        for row in r:
            if row.get("status") == "ok":
                ts.append(float(row["T"]))
    return ts


def bootstrap_vD(times, n_boot=400):
    """初通過時間の標本から v=L/T1 と D_eff のブートストラップ標準誤差を返す。"""
    n = len(times)
    if n < 2:
        return float("nan"), float("nan")
    vs, ds = [], []
    for _ in range(n_boot):
        samp = [times[random.randrange(n)] for _ in range(n)]
        t1 = sum(samp) / n
        t2 = sum(t * t for t in samp) / n
        vs.append(L / t1)
        ds.append(0.5 * L * L * (t2 - t1 * t1) / (t1 ** 3))

    def std(xs):
        mu = sum(xs) / len(xs)
        return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))
    return std(vs), std(ds)


# --- angle_hist.csv から配向量を取り出す ---------------------------------------
def load_angle_hist(combo):
    """x(畳んだ位置) -> [(phi, count), ...] を返す。"""
    by_x = defaultdict(list)
    path = os.path.join(EXP, combo, "angle_hist.csv")
    with open(path) as fh:
        for row in csv.DictReader(fh):
            by_x[round(float(row["x"]), 3)].append(
                (float(row["phi"]), float(row["count"])))
    return by_x


def nearest_x(by_x, xtarget):
    return min(by_x.keys(), key=lambda v: abs(v - xtarget))


def mean_abs_sin(data):
    """占有重み付き <|sin phi|>（= 横方向への張り出し l|sin phi| の指標）。"""
    tot = sum(c for _, c in data) or 1.0
    return sum(abs(math.sin(p)) * c for p, c in data) / tot


def pdf_phi(data):
    """P(phi) を確率密度（積分=1, rad^-1）に正規化して (phi_deg, density) で返す。"""
    data = sorted(data)
    if len(data) < 2:
        return [(math.degrees(p), 0.0) for p, _ in data]
    dphi = data[1][0] - data[0][0]
    tot = sum(c for _, c in data) * dphi or 1.0
    return [(math.degrees(p), c / tot) for p, c in data]


# x ビン中心: 0.005, 0.015, ... → 広い所/最狭窄部に最も近いビン
X_WIDE = 0.195     # omega 最大（チャネルの口）付近
X_NARROW = 0.815   # omega 最小（最狭窄部）付近


def bt(beta):
    """beta -> 列名用タグ（小数点を避ける）: 0.5->05, 1->1, ..."""
    return ("%g" % beta).replace(".", "")


def write_dat(path, header, rows, comment=None):
    # 1 行目を「# 始まりでないヘッダ行」にすることで pgfplots が列名として読む。
    with open(path, "w") as fh:
        if comment:
            for line in comment.splitlines():
                fh.write("# %s\n" % line)
        fh.write(" ".join(header) + "\n")
        for row in rows:
            fh.write(" ".join(
                ("%.6g" % v) if isinstance(v, float) else str(v)
                for v in row) + "\n")
    print("wrote", os.path.relpath(path, ROOT))


# ================================================================================
def main():
    (xmin, wmin), (xmax, wmax) = channel_extrema()

    # 各 combo の派生量をすべて集約 -------------------------------------------------
    rec = {}  # (m, beta, delta_val) -> dict
    for m in MS:
        for beta in BETAS:
            for dstr, dval in DELTAS:
                combo = combo_name(m, beta, dstr)
                s = load_summary(combo)
                times = load_times(combo)
                v = L / s["T1"]
                sev, seD = bootstrap_vD(times)
                bx = load_angle_hist(combo)
                wide = bx[nearest_x(bx, X_WIDE)]
                narrow = bx[nearest_x(bx, X_NARROW)]
                rec[(m, beta, dval)] = dict(
                    v=v, mu=s["mu"], Deff=s["D_eff"], T1=s["T1"],
                    se_v=sev, se_D=seD,
                    sin_wide=mean_abs_sin(wide),
                    sin_narrow=mean_abs_sin(narrow),
                    combo=combo)

    # 1) transport_m{m}.dat : delta 行 × beta 列 ----------------------------------
    for m in MS:
        header = ["delta"]
        for q in ["v", "sev", "D", "seD", "mu", "T1", "sinw", "sinn"]:
            for beta in BETAS:
                header.append("%s_b%s" % (q, bt(beta)))
        rows = []
        for dstr, dval in DELTAS:
            row = [dval]
            for q in ["v", "se_v", "Deff", "se_D", "mu", "T1",
                      "sin_wide", "sin_narrow"]:
                for beta in BETAS:
                    row.append(rec[(m, beta, dval)][q])
            rows.append(row)
        write_dat(os.path.join(OUT, "transport_m%d.dat" % m), header, rows,
                  comment=("m=%d  f=10\n"
                           "delta = |Delta alpha| E / p\n"
                           "v=L/T1, se*=bootstrap SE, sinw/sinn=<|sin phi|> "
                           "at wide/narrow section" % m))

    # 2) 配向分布 P(phi)（代表 combo） ---------------------------------------------
    for m in MS:
        for beta in (1.0, 3.0):
            for region, xt, tag in [("wide", X_WIDE, "wide"),
                                    ("narrow", X_NARROW, "narrow")]:
                cols = {}
                phideg = None
                for dstr, dval in DELTAS:
                    bx = load_angle_hist(combo_name(m, beta, dstr))
                    pdf = pdf_phi(bx[nearest_x(bx, xt)])
                    if phideg is None:
                        phideg = [p for p, _ in pdf]
                    cols[dstr] = [d for _, d in pdf]
                header = ["phi_deg"] + ["d%s" % s.replace(".", "")
                                        for s, _ in DELTAS]
                rows = [[phideg[i]] + [cols[s][i] for s, _ in DELTAS]
                        for i in range(len(phideg))]
                write_dat(
                    os.path.join(OUT, "pphi_%s_m%d_b%g.dat" % (tag, m, beta)),
                    header, rows,
                    comment=("P(phi) [1/rad] at %s section, m=%d beta=%g\n"
                             "columns d033 d1 d2 d3 d5 d10 = delta values"
                             % (region, m, beta)))

    # 3) collapse.dat : 配向 → 輸送の対応（全 48 combo） --------------------------
    header = ["sin_wide", "sin_narrow", "v", "Deff", "m", "beta", "delta"]
    rows = []
    for (m, beta, dval), d in sorted(rec.items()):
        rows.append([d["sin_wide"], d["sin_narrow"], d["v"], d["Deff"],
                     m, beta, dval])
    write_dat(os.path.join(OUT, "collapse.dat"), header, rows,
              comment="<|sin phi|> (wide & narrow) vs v=L/T1, all combos")
    # m 別にも分けておく（pgfplots の色分けが楽）
    for m in MS:
        rows_m = [r for r in rows if r[4] == m]
        write_dat(os.path.join(OUT, "collapse_m%d.dat" % m), header, rows_m)

    # 4) heat_m{m}.dat : v(beta, delta) のヒートマップ用（surf/matrix） -----------
    #    log2(delta) を x に使うと等間隔に近く見やすい
    for m in MS:
        header = ["delta", "log2delta", "beta", "v", "Deff", "mu"]
        rows = []
        for beta in BETAS:
            for dstr, dval in DELTAS:
                d = rec[(m, beta, dval)]
                rows.append([dval, math.log(dval, 2), beta,
                             d["v"], d["Deff"], d["mu"]])
            rows.append("")  # surf 用に scan 区切りの空行
        # write with blank-line separators
        path = os.path.join(OUT, "heat_m%d.dat" % m)
        with open(path, "w") as fh:
            fh.write("# v(beta,delta) for m=%d. blank line separates beta scans\n"
                     % m)
            fh.write(" ".join(header) + "\n")
            for row in rows:
                if row == "":
                    fh.write("\n")
                else:
                    fh.write(" ".join("%.6g" % v for v in row) + "\n")
        print("wrote", os.path.relpath(path, ROOT))

    # 5b) xphi_*.dat : (x, phi) 占有マップ（各 x で phi 方向に正規化した P(phi|x)） ---
    #     代表 combo を比較できるように、配向が揃う/傾く両極端を出力する。
    DPHI = 2 * math.pi / 36.0
    for m, beta, dstr in [(3, 3.0, "0.333333"), (3, 3.0, "10"),
                          (6, 3.0, "0.333333"), (6, 3.0, "10")]:
        bx = load_angle_hist(combo_name(m, beta, dstr))
        path = os.path.join(OUT, "xphi_m%d_b%g_d%s.dat"
                            % (m, beta, dstr.replace(".", "")))
        with open(path, "w") as fh:
            fh.write("# P(phi|x) [1/rad]: each x column normalized over phi. "
                     "blank line separates x scans (for surf)\n")
            fh.write("x phi p\n")
            for x in sorted(bx.keys()):
                col = sorted(bx[x])
                tot = sum(c for _, c in col) * DPHI or 1.0
                for phi, c in col:
                    fh.write("%.4f %.5f %.5f\n" % (x, phi, c / tot))
                fh.write("\n")
        print("wrote", os.path.relpath(path, ROOT))

    # 5) channel.dat : 壁形状 -----------------------------------------------------
    rows = []
    for i in range(401):
        x = i / 400.0
        rows.append([x, omega(x), -omega(x)])
    write_dat(os.path.join(OUT, "channel.dat"), ["x", "upper", "lower"], rows)

    # 6) meta.txt -----------------------------------------------------------------
    with open(os.path.join(OUT, "meta.txt"), "w") as fh:
        fh.write("omega_min = %.4f at x=%.4f  (full width %.4f)\n"
                 % (wmin, xmin, 2 * wmin))
        fh.write("omega_max = %.4f at x=%.4f  (full width %.4f)\n"
                 % (wmax, xmax, 2 * wmax))
        for m in MS:
            l = 2 * m * 0.8 * 0.008
            fh.write("m=%d: l=%.4f, (l/2)/omega_min=%.3f  "
                     "(=> tilt fit threshold delta ~ %.2f)\n"
                     % (m, l, (l / 2) / wmin, (l / 2) / wmin))
    print("wrote", os.path.relpath(os.path.join(OUT, "meta.txt"), ROOT))


if __name__ == "__main__":
    main()
