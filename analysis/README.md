# analysis/ — 卒論用の解析・作図

`experiments_p-60l/` のシミュレーション結果（48 combo: $m\in\{3,6\}$,
$\beta pE\in\{0.5,1,2,3\}$, $\frac{|\Delta \alpha|E}{p}\in\{1/3,1,2,3,5,10\}$, $f=10$）から、
卒論「結論」を検証するためのグラフを **pgfplots（LaTeX ネイティブ）** で作る。

## ワークフロー

```sh
# 1) 生データ -> pgfplots 用の tidy な .dat を生成（標準ライブラリのみ・numpy 不要）
python3 analysis/prepare_data.py            # -> analysis/data/*.dat

# 2) 図だけを確認（platex + dvipdfmx, ルートから実行すること）
platex  -output-directory=analysis -halt-on-error analysis/preview.tex
dvipdfmx -o analysis/preview.pdf analysis/preview.dvi
```

`prepare_data.py` は各 combo について
`summary.json`（T1, T2, mu, D_eff）, `trials.csv`（誤差棒用にブートストラップ）,
`angle_hist.csv`（占有重み付き $\langle|\sin\phi|\rangle$ と配向分布 $P(\phi)$）
を集計する。乱数シード固定。

## 本文への組み込み

本文 `1029307812_特別研究報告書2026.tex` のプリアンブル（`\begin{document}` の前）に

```latex
\input{analysis/figstyle}
```

を追加し、結果の章で各図を `figure` 環境に入れて取り込む：

```latex
\begin{figure}[t]
  \centering
  \input{analysis/fig_transport}
  \caption{平均速度 $v=L/T_1$ と有効拡散係数 $D_{\mathrm{eff}}$ の
    $\frac{|\Delta \alpha|E}{p}$ 依存性。誤差棒はブートストラップ標準誤差。}
  \label{fig:transport}
\end{figure}
```

`\figdata`（既定 `analysis/data`）はデータの場所。本文はルートでコンパイルされる前提。
`[dvipdfmx]` は documentclass の大域オプションにあるので、tikz/pgfplots は自動で
dvipdfmx ドライバを使う（追加設定不要）。

## 図の一覧と狙い

| ファイル | 図 | 検証する主張 |
| :-- | :-- | :-- |
| `fig_transport.tex` | $v, D_{\mathrm{eff}}$ vs $\frac{|\Delta \alpha|E}{p}$（$m = 3, 6$） | 主結果。$\frac{|\Delta \alpha|E}{p}$ 増で $v$ 増、$\beta pE$ との競合、$m=6$ で急峻 |
| `fig_orientation_sin.tex` | $\langle |\sin\phi|\rangle$ vs $\frac{|\Delta \alpha|E}{p}$ ＋ 理論 $\min(1, \frac{p}{|\Delta \alpha|E})$ | 張り出しが $\frac{|\Delta \alpha|E}{p}>1$ で減る（傾き機構の定量化） |
| `fig_pphi.tex` | 配向分布 $P(\phi)$ | 峰が $\pi/2$ → $\phi_1=\arcsin(\frac{p}{|\Delta \alpha|E})$ へ移動 |
| `fig_collapse.tex` | $v$ vs $\langle |\sin\phi|\rangle$（全 48 点） | 配向（張り出し）が輸送を支配する直接証拠 |
| `fig_heatmap.tex` | $v(\frac{|\Delta \alpha|E}{p},\ \beta pE)$ のヒートマップ | 分離の動作マップ。$m$ で $v$ が分かれる＝分離可能性 |

すべての combo で `passage_fraction=1.0`（全試行が 1 周期を通過）。
