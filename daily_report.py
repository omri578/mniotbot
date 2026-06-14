# -*- coding: utf-8 -*-
"""
דוח תיק יומי -> טלגרם (גרסת משימה מתוזמנת)
============================================
הסקריפט הזה רץ פעם ביום (דרך GitHub Actions), מושך מחירים ושער דולר,
מחשב רווח/הפסד, שולח לך הודעה בטלגרם — ומסיים. אין כאן בוט שרץ ברציפות,
ולכן אין צורך בשרת, בכרטיס אשראי או במחשב דלוק.

קורא שני משתני סביבה (נכנסים כ-Secrets ב-GitHub, לא בקוד):
- BOT_TOKEN : הטוקן מ-BotFather
- CHAT_ID   : מזהה הצ'אט שלך (ראה מדריך איך משיגים)
"""

import os
import sys
import requests
import yfinance as yf

# ===================== התיק שלך =====================
# ערוך כאן: שם, טיקר, כמות, מחיר קנייה, מטבע ("USD"/"ILA" אגורות/"ILS").
PORTFOLIO = [
    {"name": "אפל",   "ticker": "AAPL",    "shares": 0.25, "buy_price": 195.5,  "currency": "USD"},
    {"name": "אל על", "ticker": "ELAL.TA", "shares": 10.0, "buy_price": 1230.0, "currency": "ILA"},
    {"name": "דיסני", "ticker": "DIS",     "shares": 1.0,  "buy_price": 93.0,   "currency": "USD"},
]
# ====================================================


def get_price(ticker: str) -> float:
    t = yf.Ticker(ticker)
    try:
        p = t.fast_info["last_price"]
        if p:
            return float(p)
    except Exception:
        pass
    hist = t.history(period="1d")
    return float(hist["Close"].iloc[-1])


def to_ils(amount, currency, usdils):
    if currency == "USD":
        return amount * usdils
    if currency == "ILA":      # אגורות -> שקלים
        return amount / 100.0
    return amount              # ILS


def build_report() -> str:
    usdils = get_price("ILS=X")

    lines = ["📊 *דוח התיק היומי*", ""]
    total_cost = total_value = 0.0
    perf, errors = [], []

    for h in PORTFOLIO:
        try:
            cur = get_price(h["ticker"])
        except Exception:
            errors.append(h["name"])
            continue
        cost_ils  = to_ils(h["shares"] * h["buy_price"], h["currency"], usdils)
        value_ils = to_ils(h["shares"] * cur,            h["currency"], usdils)
        pl = value_ils - cost_ils
        pct = (cur / h["buy_price"] - 1) * 100
        total_cost += cost_ils
        total_value += value_ils
        perf.append((h["name"], pct))
        sign = "🟢" if pl >= 0 else "🔴"
        lines.append(f"{sign} {h['name']}: {pl:+.2f} ₪ ({pct:+.2f}%)")

    if total_cost == 0:
        return "⚠️ לא הצלחתי למשוך מחירים כרגע. ננסה שוב מחר."

    total_pl = total_value - total_cost
    total_pct = (total_value / total_cost - 1) * 100
    lines += [
        "",
        f"💰 שווי נוכחי: {total_value:,.2f} ₪",
        f"{'🟢' if total_pl >= 0 else '🔴'} *רווח/הפסד כולל: {total_pl:+,.2f} ₪ ({total_pct:+.2f}%)*",
        f"💵 שער דולר: {usdils:.3f} ₪",
    ]
    if errors:
        lines.append(f"⚠️ לא נמשכו: {', '.join(errors)}")

    if perf:
        best  = max(perf, key=lambda x: x[1])
        worst = min(perf, key=lambda x: x[1])
        lines += [
            "",
            f"📈 הכי חזקה: {best[0]} ({best[1]:+.2f}%) | 📉 הכי חלשה: {worst[0]} ({worst[1]:+.2f}%)",
            "_מגמה בלבד, לא ייעוץ השקעות._",
        ]
    return "\n".join(lines)


def send_telegram(text: str):
    token = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }, timeout=30)
    resp.raise_for_status()


def main():
    if not os.environ.get("BOT_TOKEN") or not os.environ.get("CHAT_ID"):
        print("חסר BOT_TOKEN או CHAT_ID במשתני הסביבה.", file=sys.stderr)
        sys.exit(1)
    report = build_report()
    send_telegram(report)
    print("נשלח בהצלחה:\n" + report)


if __name__ == "__main__":
    main()
