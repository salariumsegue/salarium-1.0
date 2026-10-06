"""Preserve published rebalance snapshots without inventing point-in-time inputs."""
import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = 'web/public/data/forward_paper_snapshot.json'
OUTPUT = ROOT / 'web/public/data/decision_archive.json'
LEDGER = 'reports/shadow/drawdown_budget_shadow_ledger.csv'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def entry_from_bytes(raw, ledger_raw, commit):
    snapshot = json.loads(raw)
    portfolio = snapshot['forward_portfolio']
    if not portfolio.get('rebalance_performed'):
        return None
    date = portfolio['last_rebalance_date']
    ledger = list(csv.DictReader(io.StringIO(ledger_raw.decode())))
    row = next((r for r in ledger if r['rebalance_date'] == date), None)
    if row is None:
        raise ValueError('Rebalance snapshot lacks its ledger event')
    return {'date': date, 'available_at': snapshot['generated_at_utc'],
            'published_commit': commit,
            'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
            'raw_utf8': raw.decode(), 'snapshot': snapshot, 'ledger': row}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--include-working', action='store_true')
    args = parser.parse_args()
    if args.include_working:
        # Scheduled updates append only; the Git-history import is a one-time seed.
        entries = json.loads(OUTPUT.read_text())['entries']
        entry = entry_from_bytes((ROOT / ARTIFACT).read_bytes(), (ROOT / LEDGER).read_bytes(), None)
        if entry and entry['date'] not in {e['date'] for e in entries}:
            entries.append(entry)
    else:
        entries = []
        seen = set()
        for commit in git('log', '--reverse', '--format=%H', '--', ARTIFACT).decode().splitlines():
            entry = entry_from_bytes(git('show', f'{commit}:{ARTIFACT}'), git('show', f'{commit}:{LEDGER}'), commit)
            if entry and entry['date'] not in seen:
                seen.add(entry['date'])
                entries.append(entry)
    if not entries:
        raise RuntimeError('No recorded rebalances found')
    OUTPUT.write_text(json.dumps({'schema_version': '1.0', 'coverage': 'Recorded rebalance snapshots preserved from Git history and subsequent governed publications; not a complete raw-input archive.', 'entries': entries}, indent=2) + '\n')
    print(f'Preserved {len(entries)} recorded rebalances')


if __name__ == '__main__':
    main()
