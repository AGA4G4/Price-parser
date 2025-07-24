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

def extract_prices(text):
    lines = text.splitlines()
    price_data = {}
    for line in lines:
        if any(x in line for x in ["تومان", "☎️", "تماس", "🤙"]):
            match = re.search(
                r'(تیر\s*\d+\s*[^\d:،\n]*)'  # نام کالا تا اولین عدد قیمت
                r'[:\s\-]*'
                r'([\d۰-۹\/\,]+|☎️|تماس|🤙)?', line)
            if not match:
                continue
            item = match.group(1).strip().replace("\u200c", " ")
            price_str = match.group(2)

            if price_str is None:
                price_data[item] = "Call"
                continue

            price_str = price_str.strip()

            if any(x in price_str for x in ["☎️", "تماس", "🤙"]) or not re.search(r'\d', price_str):
                price_data[item] = "Call"
            else:
                normalized = normalize_price_str(price_str)
                if normalized.isdigit():
                    price_data[item] = int(normalized)
                else:
                    price_data[item] = "Call"
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
    parts = date.split('/')
    dir_path = Path('logs') / parts[0] / parts[1]
    os.makedirs(dir_path, exist_ok=True)
    file_path = dir_path / f"{parts[2]}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"date": date, "prices": prices}, f, ensure_ascii=False, indent=2)

def maintain_latest_logs(keep=2):
    log_dir = Path("logs")
    if not log_dir.exists():
        return
    log_files = sorted(log_dir.glob("**/*.json"), key=lambda f: f.name, reverse=True)
    for old_file in log_files[keep:]:
        try:
            old_file.unlink()
        except Exception:
            continue

def get_latest_two_logs():
    log_dir = Path("logs")
    if not log_dir.exists():
        return []
    log_files = sorted(log_dir.glob("**/*.json"), key=lambda f: f.name, reverse=True)
    latest = []
    for file in log_files[:2]:
        try:
            with open(file, "r", encoding="utf-8") as f:
                latest.append(json.load(f))
        except Exception:
            continue
    return latest[::-1]  # Oldest first

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
        candles = {item: "⏸" if today_prices[item] != "Call" else "☎️" for item in today_prices}

    # Format prices for readability
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
