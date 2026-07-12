
"""
Data parser for WeChat public account exports.
"""
import pandas as pd
import os
import re
from bs4 import BeautifulSoup


def parse_read_excel(file_paths):
    all_channel = []
    all_summary = []
    all_article = []

    for fp in sorted(file_paths):
        try:
            df = pd.read_excel(fp, header=None, dtype=str)
        except Exception:
            continue
        df = df.fillna('')
        n_rows = len(df)

        for i in range(3, n_rows):
            date_str = str(df.iloc[i, 1]).strip()
            channel = str(df.iloc[i, 2]).strip()
            readers_raw = str(df.iloc[i, 3]).strip()
            if not date_str or not channel:
                continue
            try:
                readers_int = int(float(readers_raw))
            except (ValueError, TypeError):
                continue
            all_channel.append({
                'date': pd.to_datetime(date_str),
                'channel': channel,
                'readers': readers_int,
            })

        for i in range(3, n_rows):
            date_str = str(df.iloc[i, 5]).strip()
            if not date_str or not re.match(r'20\d{2}', date_str):
                continue
            all_summary.append({
                'date': pd.to_datetime(date_str),
                'shares': _safe_int(df.iloc[i, 6]),
                'clicks': _safe_int(df.iloc[i, 7]),
                'favorites': _safe_int(df.iloc[i, 8]),
                'articles': _safe_int(df.iloc[i, 9]),
            })

        for i in range(3, n_rows):
            title = str(df.iloc[i, 13]).strip()
            if not title:
                continue
            date_val = str(df.iloc[i, 12]).strip()
            try:
                date_dt = pd.to_datetime(date_val)
            except Exception:
                date_dt = date_val
            all_article.append({
                'channel': str(df.iloc[i, 11]).strip(),
                'date': date_dt,
                'title': title,
                'readers': _safe_int(df.iloc[i, 14]),
                'ratio': _safe_float(df.iloc[i, 15]),
            })

    result = {}
    if all_channel:
        result['daily_by_channel'] = pd.DataFrame(all_channel)
    if all_summary:
        result['daily_summary'] = pd.DataFrame(all_summary)
    if all_article:
        result['article_ranking'] = pd.DataFrame(all_article)
    return result


def parse_fans_excel(file_paths):
    """Parse HTML-format fans data files using BeautifulSoup."""
    all_records = []

    for fp in sorted(file_paths):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            table = soup.find('table')
            if not table:
                continue
            rows = table.find_all('tr')
            for row in rows[3:]:
                cells = row.find_all('th')
                if len(cells) < 5:
                    continue
                vals = [c.get_text(strip=True) for c in cells]
                date_str = vals[0]
                if not re.match(r'20\d{2}-\d{2}-\d{2}', date_str):
                    continue
                record = {
                    'date': pd.to_datetime(date_str),
                    '\u65b0\u5173\u6ce8\u4eba\u6570': _safe_int_or_none(vals[1]),
                    '\u53d6\u6d88\u5173\u6ce8\u4eba\u6570': _safe_int_or_none(vals[2]),
                    '\u51c0\u589e\u5173\u6ce8\u4eba\u6570': _safe_int_or_none(vals[3]),
                    '\u7d2f\u79ef\u5173\u6ce8\u4eba\u6570': _safe_int_or_none(vals[4]),
                }
                all_records.append(record)
        except Exception:
            continue

    if all_records:
        df = pd.DataFrame(all_records).drop_duplicates(subset='date').sort_values('date')
        return {'fans_data': df}
    return {}


def _safe_int(val):
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return 0


def _safe_int_or_none(val):
    s = str(val).strip()
    if s == '-' or s == '':
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _safe_float(val):
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return 0.0
