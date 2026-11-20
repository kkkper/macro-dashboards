# 總經儀表板 Macro Dashboards

兩套總經監控儀表板的整合 repo，供 GitHub 綁定與 Devin Bot 後續維護使用。

## 專案概覽

| 儀表板 | 路徑 | 說明 |
| --- | --- | --- |
| 美股總經雷達 | `us-radar/index.html` | 追蹤影響美股與 Bitcoin 的關鍵美國總經指標，繁體中文、台灣時間呈現，一眼紅綠判讀 |
| 台股總經儀表板 | `taiwan-dashboard/index.html` | 台股總經 × 資金流 × 產業景氣：市場趨勢／資金風險／產業基本面／總經估值壓力四軸獨立判讀，不做單一 0–100 總分 |
| 入口頁 | `index.html` | 兩套儀表板的連結入口 |

## Repo 結構

```
.
├── index.html                  # 入口頁
├── us-radar/
│   └── index.html              # 美股總經雷達
├── taiwan-dashboard/
│   └── index.html              # 台股總經儀表板
├── adapters/
│   ├── fred_fetch.py           # FRED 抓取 helper（金鑰讀環境變數 FRED_API_KEY）
│   └── twse_bfi82u_adapter.py  # TWSE 三大法人 BFI82U 金額解析
├── PLAYBOOK.md                 # Devin Bot 維運手冊
└── README.md
```

## 資料來源

全數官方來源，優先順序：JSON/API > CSV/ZIP > 官網結構化下載 > 瀏覽器擷取（最後手段）。

- **美股雷達**：FRED（聖路易斯聯儲，`adapters/fred_fetch.py` 抓取）、ISM（製造業／服務業 PMI）、CME FedWatch（利率期貨隱含機率）。預期值來源為 Investing.com 經濟日曆。
- **台股儀表板**：TWSE（臺灣證券交易所，含 BFI82U 三大法人金額）、TPEx（櫃買中心）、TAIFEX（期交所）、CBC（中央銀行）、MOF 財政部（data.gov.tw）、NDC 國發會、MOEA 經濟部、DGBAS 主計總處；美國 10 年期實質利率用 FRED DFII10。

## 更新節奏

- **美股雷達**：每日 08:00（Asia/Taipei）定期刷新；★ 重大數據公布後 30 分鐘內再刷新一次。
- **台股儀表板**：盤後分批更新（交易日收盤後批次抓取官方端點）。

## 鐵律（Iron Rules，所有維護者含 Devin Bot 必須遵守）

1. **不編造、不估計數據。** 缺資料就顯示「暫無資料」，缺預期就顯示「暫無預期」，缺預告就顯示「暫無預告」。過期或不一致的來源要照實標示，不可平滑帶過。
2. **Secrets 只放後台，絕不寫進頁面程式碼。** FRED API Key 只能透過環境變數 `FRED_API_KEY` 在伺服端讀取（見 `adapters/fred_fetch.py`）；任何金鑰、token 都不得出現在 HTML、JS 或 commit 歷史裡。
3. **口徑不可混加。** BFI82U 是三大法人「金額」，絕不可與 T86 的個股「股數」相加；P/C 未平倉量比與成交量比分開呈現、不交叉比較；USD/TWD 上升代表台幣貶值。
4. **版面變更需 Kuo 確認。** 版面、結構、判讀規則的改動要先經 Kuo 核准；資料修復與 adapter 修正一律走 PR，附原因與改法摘要。

## 維運

排程刷新、故障處理流程（抓取失敗／403／日期停滯的處理順序）見 [PLAYBOOK.md](PLAYBOOK.md)。
