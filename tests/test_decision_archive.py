import hashlib
import json
from pathlib import Path
import pytest
from scripts.export_decision_archive import entry_from_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_archived_decisions_preserve_original_bytes_and_event():
    archive = json.loads((ROOT / 'web/public/data/decision_archive.json').read_text())
    dates = [e['date'] for e in archive['entries']]
    assert len(dates) == len(set(dates))
    assert dates == sorted(dates)
    for e in archive['entries']:
        assert hashlib.sha256(e['raw_utf8'].encode()).hexdigest() == e['snapshot_sha256']
        assert json.loads(e['raw_utf8']) == e['snapshot']
        assert e['ledger']['rebalance_date'] == e['date']
        assert e['snapshot']['forward_portfolio']['rebalance_performed'] is True
        assert e['available_at'] == e['snapshot']['generated_at_utc']
        assert e['snapshot']['governance']['live_capital'] is False


def test_non_rebalance_is_not_reconstructed_as_a_decision():
    raw = json.dumps({'forward_portfolio': {'rebalance_performed': False}}).encode()
    assert entry_from_bytes(raw, b'', None) is None


def test_missing_ledger_event_fails_closed():
    raw = json.dumps({'forward_portfolio': {'rebalance_performed': True, 'last_rebalance_date': '2026-09-23'}}).encode()
    with pytest.raises(ValueError, match='lacks its ledger event'):
        entry_from_bytes(raw, b'rebalance_date\n2026-09-09\n', None)


def test_working_archive_export_does_not_change_existing_records():
    import subprocess
    target = ROOT / 'web/public/data/decision_archive.json'
    before = target.read_bytes()
    subprocess.run(['python3', str(ROOT / 'scripts/export_decision_archive.py'), '--include-working'], check=True)
    assert target.read_bytes() == before


def test_bundle_return_stream_reproduces_published_metrics():
    import math
    stream = json.loads((ROOT / 'web/public/data/research_return_stream.json').read_text())
    account = json.loads((ROOT / 'web/public/data/hypothetical_account_snapshot.json').read_text())
    growth = math.prod(1 + r['net_return'] for r in stream['observations'])
    annualized = growth ** ((252 / stream['model']['rebalance_every_days']) / len(stream['observations'])) - 1
    assert abs(annualized - account['statistics']['annualized_net_return']) < 1e-10
