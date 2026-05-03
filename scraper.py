#!/usr/bin/env python3
import os
import subprocess
import csv
import sys
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime

ACHIEVEMENT_URL = 'https://hackmyvm.eu/achievement/?achievement={}'

class AchievementScraper:
    def __init__(self, output_path):
        self.output_path = output_path
        self._ensure_directory()

    def _ensure_directory(self):
        d = os.path.dirname(self.output_path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _get_last_id_from_csv(self):
        if not os.path.exists(self.output_path):
            return 0
        try:
            with open(self.output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) < 2:
                    return 0
                # read header and last line
                last_line = lines[-1].strip()
                if not last_line:
                    return 0
                reader = csv.reader([lines[0], last_line])
                header = next(reader)
                last_record = next(reader)
                if 'id' in header:
                    id_index = header.index('id')
                    return int(last_record[id_index])
        except Exception:
            return 0
        return 0

    def _parse_page(self, html, achievement_id):
        soup = BeautifulSoup(html, 'html.parser')
        data = {
            'id': achievement_id,
            'nickname': '',
            'date': '',
            'vm_title': None,
            'difficulty': 'unknown',
            'rank': ''
        }
        try:
            nickname_elem = soup.select_one('h4.user')
            if nickname_elem:
                data['nickname'] = nickname_elem.get_text().strip()

            date_elem = soup.select_one('span.date')
            if date_elem:
                data['date'] = date_elem.get_text(strip=True)

            vm_elems = soup.select('h3')
            if len(vm_elems) > 1:
                vm_elem = vm_elems[1]
                data['vm_title'] = vm_elem.get_text(strip=True)
                classes = vm_elem.get('class') or []
                for cls in ['Easy', 'Medium', 'Hard']:
                    if cls in classes:
                        data['difficulty'] = cls.lower()
                        break

            rank_elem = soup.select_one('p.ranked')
            if rank_elem:
                rank_text = rank_elem.get_text(strip=True)
                if rank_text.startswith('#'):
                    data['rank'] = rank_text.split()[0][1:]

            if not data['vm_title'] or not data['nickname']:
                return None
            return data
        except Exception:
            return None

    def _save_to_csv(self, records):
        if not records:
            return
        file_exists = os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0
        fieldnames = list(records[0].keys())
        try:
            with open(self.output_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(records)
        except IOError as e:
            print(f"[!] Error saving to CSV: {e}")


    def crawl(self, start_id=None, verbose=False, max_count=5000, batch_size=50, log_action=True):
        last_id = self._get_last_id_from_csv()
        if start_id is None:
            start_id = last_id + 1
        new_records = []
        consecutive_empty_ids = 0
        total_new = 0

        def action_log(msg):
            if log_action:
                print(f"[ACTION] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

        if verbose:
            print(f"[*] Starting crawl from ID {start_id}")
        action_log(f"Start crawl from ID {start_id}")

        max_retry = 2
        empty_limit = 5
        session = requests.Session()
        aid = start_id

        while True:
            success = False
            for retry_count in range(max_retry):
                url = ACHIEVEMENT_URL.format(aid)
                try:
                    r = session.get(url, timeout=10)
                except requests.RequestException as e:
                    action_log(f"{aid}: network error: {e} (retry {retry_count+1}/{max_retry})")
                    if verbose:
                        print(f"[!] {aid}: network error: {e} (retry {retry_count+1}/{max_retry})")
                    continue
                if r.status_code != 200:
                    action_log(f"{aid}: HTTP {r.status_code} (retry {retry_count+1}/{max_retry})")
                    if verbose:
                        print(f"[-] {aid}: HTTP {r.status_code} (retry {retry_count+1}/{max_retry})")
                    continue
                data = self._parse_page(r.text, aid)
                if data:
                    new_records.append(data)
                    total_new += 1
                    consecutive_empty_ids = 0
                    action_log(f"Found ID {aid} - {data['nickname']} - {data['vm_title']}")
                    if verbose:
                        print(f"[+] Found ID {aid} - {data['nickname']} - {data['vm_title']}")
                    if len(new_records) >= batch_size:
                        self._save_to_csv(new_records)
                        action_log(f"Batch saved {len(new_records)} records to CSV.")
                        new_records = []
                    success = True
                    break
                else:
                    action_log(f"{aid}: no data (retry {retry_count+1}/{max_retry})")
                    if verbose:
                        print(f"[*] {aid}: no data (retry {retry_count+1}/{max_retry})")
                    continue
            if not success:
                consecutive_empty_ids += 1
                action_log(f"{aid}: failed after {max_retry} retries. ({consecutive_empty_ids}/{empty_limit})")
                if verbose:
                    print(f"[-] {aid}: failed after {max_retry} retries. ({consecutive_empty_ids}/{empty_limit})")
                if consecutive_empty_ids >= empty_limit and aid >= 34000:
                    action_log(f"Reached {empty_limit} consecutive empty pages, stopping.")
                    break
            else:
                consecutive_empty_ids = 0
            aid += 1
        if new_records:
            self._save_to_csv(new_records)
            action_log(f"Final batch saved {len(new_records)} records to CSV.")
        action_log(f"Crawl finished. New records: {total_new}")
        if verbose:
            print(f"[*] Crawl finished. New records: {total_new}")
        return total_new


def main():
    parser = argparse.ArgumentParser(description='HackMyVM Achievement scraper (no-login)')
    parser.add_argument('--start', type=int, help='Start ID to crawl from')
    parser.add_argument('--output', type=str, default='data/achievements.csv', help='Output CSV path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()


    scraper = AchievementScraper(args.output)
    try:
        new = scraper.crawl(
            start_id=args.start,
            verbose=args.verbose,
            batch_size=50,
            log_action=True
        )
        print(f"New records added: {new}")
    except KeyboardInterrupt:
        print('\n[!] Interrupted by user')
        sys.exit(1)


if __name__ == '__main__':
    main()
