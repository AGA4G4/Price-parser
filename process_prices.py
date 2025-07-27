import re
import json
import os
from pathlib import Path

def extract_date(text):
    match = re.search(r'تاریخ[:\s\u200c]+(\d{4}/\d{2}/\d{2})', text)
    return match.group(1) if match else None

def normalize_price_str(price_str):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    trans_table = str.maketrans(persian_digits, english_digits)
    normalized = price_str.translate(trans_table).replace("/", "").replace(",", "").replace(" ", "")
    return normalized

def is_valid_price(price_str):
    normalized = normalize_price_str(price_str)
    return normalized.isdigit() and len(normalized) >= 4

def extract_prices(text):
    lines = text.splitlines()
    price_data = {}

    
    tir_regex = re.compile(r'(تیر\s*\d{1,2}(?:\s*[^۰-۹\d\s:،\n]*)\s*(?:تهران|بناب|اهواز|یزد|اصفهان|امیرکبیر|نیشابور|سمنان)?)\s*[:\-]*\s*([\d۰-۹\/\,]+)?')

    # نبشی (Nabshi)
    nabshi_regex = re.compile(r'(نبشی\s*[۰-۹\d]+\s*وزن\s*[\d۰-۹\/\.\٫]+\s*کیلو)\s*([\d۰-۹\/\,]+)?')

    # سپری (Separi)
    separi_regex = re.compile(r'(?:✅️)?\s*(سپری\s*[۰-۹\d]+\s*وزن\s*[\d۰-۹\d\/\.\٫]+\s*کیلو)\s*([\d۰-۹\d\/\,]+|تماس)?')

    # ناودانی (Navdani) 
    navdani_regex = re.compile(r'(?:✅️)?\s*(ناودانی\s*[۰-۹\d]+(?:\s*[\d۰-۹\d\/\.\٫]+)?\s*کیلو)\s*([\d۰-۹\d\/\,]+|تماس)?')

    # تیرچه (Tirche)
    tirche_regex = re.compile(r'(?:✅️)?\s*(تیرچه(?:\s+فولاد\s+\S+|\s+تهران)?)\s*([\d۰-۹\d\/\,]+|تماس)?')

    # قوطی (Ghoti)
    ghoti_regex = re.compile(r'(?:✅️)?\s*(قوطی[۰-۹\d]+میل\s*[\d×xX]+\s*وزن\s*[\d۰-۹\/\.\٫]+(?:\s*کیلو)?)\s*([\d۰-۹\/\,]+)?')

    # میلگرد (Grouped or Individual) — fixed to detect سمنان & allow city (A3) tags
    milgard_regex = re.compile(
        r'میلگرد(?:\s*|\s*\()([۰-۹\d\.]+)[\)\s]*([^\d\s()،:]*?(?:\([^)]+\))?)?\s+([\d۰-۹\d/,]+)?'
    )

    for line in lines:
        line = line.strip()

        # Grouped or individual میلگرد
        mil_match = milgard_regex.search(line)
        if mil_match:
            sizes = mil_match.group(1).split(".")
            variation = mil_match.group(2) or ""
            price_str = mil_match.group(3)

            for size in sizes:
                item = f"میلگرد {size.strip()} {variation.strip()}".strip()
                if not price_str or any(k in price_str for k in ["☎️", "تماس", "🤙"]) or not is_valid_price(price_str):
                    price_data[item] = "Call"
                else:
                    price_data[item] = int(normalize_price_str(price_str))
            continue

        # Other items
        for regex in [tir_regex, nabshi_regex, separi_regex, navdani_regex, tirche_regex, ghoti_regex]:
            match = regex.search(line)
            if match:
                item = match.group(1).strip().replace("\u200c", " ")
                price_str = match.group(2)

                if not price_str or any(k in price_str for k in ["☎️", "تماس", "🤙"]) or not is_valid_price(price_str):
                    price_data[item] = "Call"
                else:
                    price_data[item] = int(normalize_price_str(price_str))
                break

    return price_data

def format_price(value):
    return f"{value:,}".replace(",", "/") if isinstance(value, int) else "تماس"

def compare_with_yesterday(today_prices, yesterday_prices):
    candles = {}
    for item, today_price in today_prices.items():
        y_price = yesterday_prices.get(item)
        if today_price == "Call":
            candles[item] = "⏸"
        elif isinstance(today_price, int):
            if isinstance(y_price, int):
                if today_price > y_price:
                    candles[item] = "🔼"
                elif today_price < y_price:
                    candles[item] = "🔽"
                else:
                    candles[item] = "⏸"
            else:
                candles[item] = "⏸"
        else:
            candles[item] = "⏸"
    return candles

def save_prices(date, prices):
    date_str = date.replace("/", "-")
    dir_path = Path("logs")
    os.makedirs(dir_path, exist_ok=True)
    file_path = dir_path / f"{date_str}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"date": date, "prices": prices}, f, ensure_ascii=False, indent=2)

def maintain_latest_logs(keep=2):
    log_dir = Path("logs")
    if not log_dir.exists():
        return
    log_files = sorted(log_dir.glob("*.json"), key=lambda f: f.stem, reverse=True)
    for old_file in log_files[keep:]:
        try:
            old_file.unlink()
        except Exception:
            continue

def get_latest_two_logs():
    log_dir = Path("logs")
    if not log_dir.exists():
        return []

    def extract_date_key(path):
        try:
            y, m, d = map(int, path.stem.split("-"))
            return (y, m, d)
        except Exception:
            return (0, 0, 0)

    log_files = sorted(log_dir.glob("*.json"), key=extract_date_key, reverse=True)

    latest = []
    for file in log_files[:2]:
        try:
            with open(file, "r", encoding="utf-8") as f:
                latest.append(json.load(f))
        except Exception:
            continue

    return latest[::-1]

def main():
    txt_file = "received_messages.txt"
    if not os.path.isfile(txt_file):
        print(f"❌ Error: {txt_file} file not found.")
        return

    with open(txt_file, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print("❌ Error: Input text file is empty.")
        return

    today_date = extract_date(text)
    if today_date is None:
        print("❌ Error: تاریخ در متن یافت نشد.")
        return

    today_prices = extract_prices(text)
    if not today_prices:
        print("❌ Error: هیچ قیمتی یافت نشد.")
        return

    save_prices(today_date, today_prices)
    maintain_latest_logs(keep=2)
    latest_logs = get_latest_two_logs()

    if len(latest_logs) == 2:
        prev_prices = latest_logs[0]["prices"]
        candles = compare_with_yesterday(today_prices, prev_prices)
    else:
        candles = {item: "⏸" for item in today_prices}

    formatted_prices = {item: format_price(price) for item, price in today_prices.items()}

    output = {
        "date": today_date,
        "prices": formatted_prices,
        "candles": candles
    }

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
