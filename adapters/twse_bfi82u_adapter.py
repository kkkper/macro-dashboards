"""台股儀表板 · 核心 adapter 片段（TWSE BFI82U 三大法人金額解析）

- 資料來源：TWSE BFI82U（三大法人買賣金額，金額口徑）
- 鐵律：BFI82U 是「金額」；T86 是個股「股數」，兩者不可相加
- 民國日期（如 1151119）正規化為 ISO 日期（2026-11-19）後另存
"""
import json
import urllib.request
from datetime import date

TWSE_BFI82U = (
    "https://www.twse.com.tw/rwd/zh/fund/BFI82U"
    "?dayDate={yyyymmdd}&response=json&type=day"
)


def roc_to_iso(roc: str) -> str:
    """民國日期轉西元 ISO：'1151119' -> '2026-11-19'（民國年 + 1911）。"""
    roc = roc.strip()
    year = int(roc[:-4]) + 1911
    return f"{year:04d}-{roc[-4:-2]}-{roc[-2:]}"


def fetch_bfi82u(day: date) -> dict | None:
    """抓單日三大法人金額；無交易日（如假日）TWSE 回 stat != OK，回 None 跳過。"""
    url = TWSE_BFI82U.format(yyyymmdd=day.strftime("%Y%m%d"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("stat") != "OK":
        return None  # 例：2026-10-23、10-26 回「沒有符合條件的資料」
    return payload


def parse_institutional_amounts(payload: dict) -> dict:
    """解析 BFI82U 列：金額原始單位為元，統一換算為億元（四捨五入 2 位）。

    只取「外資及陸資（不含外資自營商）」列作外資現貨口徑；
    自營商的自行買賣與避險分列，不併入外資。
    """
    out = {}
    for row in payload["data"]:
        name = row[0].strip()
        buy, sell, diff = (float(str(v).replace(",", "")) for v in row[1:4])
        out[name] = {
            "buy_yi": round(buy / 1e8, 2),
            "sell_yi": round(sell / 1e8, 2),
            "net_yi": round(diff / 1e8, 2),
        }
    foreign = out["外資及陸資(不含外資自營商)"]
    return {"foreign_net_yi": foreign["net_yi"], "all": out}


def cumulative_foreign_net(days: list[date]) -> dict:
    """逐日查詢加總 5／20 日累計（跳過無交易日），與單日值分開呈現。"""
    nets = []
    for d in days:
        payload = fetch_bfi82u(d)
        if payload is None:
            continue
        nets.append(parse_institutional_amounts(payload)["foreign_net_yi"])
    return {
        "latest_yi": nets[-1] if nets else None,
        "cum5_yi": round(sum(nets[-5:]), 2),
        "cum20_yi": round(sum(nets[-20:]), 2),
    }


# 實跑結果（2026-11-19 觀測日，2026-11-20 階段 3 接入時產出）：
# foreign_net_yi = -243.12 億；5 日累計 -1,803.22 億；20 日累計 -10,830.29 億
