#!/usr/bin/env python3
"""
Link Check Manager - Manage documentation instance link check records.

Tracks which instances have been checked for broken links and their fix status.
All record file operations should go through this script to avoid manual editing errors.

Usage:
  python3 link_check_manager.py --worktree-dir DIR --init
  python3 link_check_manager.py --worktree-dir DIR --count
  python3 link_check_manager.py --worktree-dir DIR --zh --get [N]
  python3 link_check_manager.py --worktree-dir DIR --en --get [N]
  python3 link_check_manager.py --worktree-dir DIR --zh --update <instance_id> <status>
  python3 link_check_manager.py --worktree-dir DIR --en --update <instance_id> <status>
"""

import json
import argparse
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

VALID_STATUSES = ['init', 'editing', 'failed', 'done']
DEFAULT_RECORD_FILE = '~/.zego-docs-fix-links-record.json'


def get_record_file_path(record_file_arg=None):
    """Get the expanded record file path."""
    path = record_file_arg or DEFAULT_RECORD_FILE
    return os.path.expanduser(path)


def load_records(record_file):
    """Load records from JSON file. Return empty structure if file doesn't exist."""
    path = get_record_file_path(record_file)
    if not os.path.exists(path):
        return {"zh": [], "en": []}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(json.dumps({"error": f"Failed to load records: {e}. Try running --init first."}),
              file=sys.stderr)
        sys.exit(1)


def save_records(records, record_file):
    """Save records to JSON file using atomic write."""
    path = get_record_file_path(record_file)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Atomic write: write to temp file then rename
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        print(json.dumps({"error": f"Failed to save records: {e}"}), file=sys.stderr)
        sys.exit(1)


def load_config_instances(language, worktree_dir):
    """Load instances from docuo.config.{zh|en}.json."""
    config_path = os.path.join(worktree_dir, f'docuo.config.{language}.json')
    if not os.path.exists(config_path):
        print(json.dumps({"error": f"Config file not found: {config_path}"}), file=sys.stderr)
        sys.exit(1)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        instances = config.get('instances', [])
        return [inst.get('id', '') for inst in instances if inst.get('id')]
    except (json.JSONDecodeError, IOError) as e:
        print(json.dumps({"error": f"Failed to load config: {e}"}), file=sys.stderr)
        sys.exit(1)


def count_unchecked(records):
    """Count unchecked instances (status != 'done') for each language."""
    counts = {}
    for lang in ['zh', 'en']:
        unchecked = [i for i in records.get(lang, []) if i.get('status') != 'done']
        counts[lang] = len(unchecked)
    return counts


def get_unchecked_ids(records, language, config_ids):
    """Get list of unchecked instance IDs for a language, preserving config order."""
    lang_records = records.get(language, [])
    record_map = {r['instance_id']: r for r in lang_records}

    unchecked = []
    for inst_id in config_ids:
        rec = record_map.get(inst_id)
        if not rec or rec.get('status') != 'done':
            unchecked.append(inst_id)
    return unchecked


def update_status(records, language, instance_id, status):
    """Update an instance's status. Returns the updated record or None if not found."""
    lang_records = records.get(language, [])
    for rec in lang_records:
        if rec['instance_id'] == instance_id:
            rec['status'] = status
            rec['last_fix_time'] = datetime.now().strftime('%Y-%m-%d')
            return rec
    return None


def initialize_records(record_file):
    """Generate initial records from both config files."""
    records = {"zh": [], "en": []}
    for lang in ['zh', 'en']:
        instance_ids = load_config_instances(lang, args.worktree_dir)
        for inst_id in instance_ids:
            records[lang].append({
                "instance_id": inst_id,
                "status": "init",
                "last_fix_time": "1970-01-01"
            })
    save_records(records, record_file)
    return records


def ensure_records(record_file):
    """Load records, auto-initialize if file missing or all instances are done."""
    records = load_records(record_file)
    path = get_record_file_path(record_file)

    needs_init = False
    if not os.path.exists(path):
        needs_init = True
    else:
        # Check if all instances across both languages are done
        all_done = True
        for lang in ['zh', 'en']:
            for rec in records.get(lang, []):
                if rec.get('status') != 'done':
                    all_done = False
                    break
            if not all_done:
                break
        if all_done and (records.get('zh') or records.get('en')):
            needs_init = True

    if needs_init:
        records = initialize_records(record_file)
    return records


def handle_count(args):
    """Handle --count command."""
    records = ensure_records(args.record_file)
    result = {"zh": 0, "en": 0}
    for lang in ['zh', 'en']:
        config_ids = load_config_instances(lang, args.worktree_dir)
        unchecked = get_unchecked_ids(records, lang, config_ids)
        result[lang] = len(unchecked)
    print(json.dumps(result, ensure_ascii=False))


def handle_get(args):
    """Handle --get command."""
    language = args.language
    count = args.get if args.get is not None else 1

    if count < 1:
        print(json.dumps({"error": "Count must be a positive integer"}), file=sys.stderr)
        sys.exit(1)

    records = ensure_records(args.record_file)
    config_ids = load_config_instances(language, args.worktree_dir)
    unchecked = get_unchecked_ids(records, language, config_ids)

    if not unchecked:
        print(json.dumps({
            "language": language,
            "instances": [],
            "count": 0,
            "message": "All instances checked."
        }, ensure_ascii=False))
        return

    selected = unchecked[:count]
    print(json.dumps({
        "language": language,
        "instances": selected,
        "count": len(selected)
    }, ensure_ascii=False))


def handle_update(args):
    """Handle --update command."""
    language = args.language
    instance_id = args.update[0]
    status = args.update[1]

    if status not in VALID_STATUSES:
        print(json.dumps({
            "error": f"Invalid status '{status}'. Valid values: {', '.join(VALID_STATUSES)}"
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    records = load_records(args.record_file)

    # If instance not in records yet (new instance added to config), add it
    lang_records = records.get(language, [])
    exists = any(r['instance_id'] == instance_id for r in lang_records)

    if not exists:
        # Check if the instance exists in config
        config_ids = load_config_instances(language, args.worktree_dir)
        if instance_id not in config_ids:
            print(json.dumps({
                "error": f"Instance '{instance_id}' not found in {language} config"
            }, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        # Add new record
        records.setdefault(language, []).append({
            "instance_id": instance_id,
            "status": status,
            "last_fix_time": datetime.now().strftime('%Y-%m-%d')
        })
        save_records(records, args.record_file)
        print(json.dumps({
            "language": language,
            "instance_id": instance_id,
            "status": status,
            "last_fix_time": datetime.now().strftime('%Y-%m-%d')
        }, ensure_ascii=False))
        return

    updated = update_status(records, language, instance_id, status)
    if updated:
        save_records(records, args.record_file)
        print(json.dumps({
            "language": language,
            "instance_id": instance_id,
            "status": updated['status'],
            "last_fix_time": updated['last_fix_time']
        }, ensure_ascii=False))
    else:
        print(json.dumps({
            "error": f"Instance '{instance_id}' not found in {language} records"
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


def handle_init(args):
    """Handle --init command."""
    records = initialize_records(args.record_file)
    zh_count = len(records.get('zh', []))
    en_count = len(records.get('en', []))
    print(json.dumps({
        "zh": zh_count,
        "en": en_count,
        "total": zh_count + en_count
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description='Manage link check instance records',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Language selection
    parser.add_argument('--zh', dest='language', action='store_const', const='zh',
                        help='Specify Chinese instances')
    parser.add_argument('--en', dest='language', action='store_const', const='en',
                        help='Specify English instances')

    # Commands
    parser.add_argument('--count', action='store_true',
                        help='Return counts of unchecked instances (zh/en)')
    parser.add_argument('--get', metavar='N', nargs='?', type=int, const=1, default=None,
                        help='Get N unchecked instance IDs (default 1)')
    parser.add_argument('--update', nargs=2, metavar=('INSTANCE_ID', 'STATUS'),
                        help='Update instance status (init|editing|failed|done)')
    parser.add_argument('--init', action='store_true',
                        help='Force reinitialize record file from config files (overwrites existing)')

    # Required
    parser.add_argument('--worktree-dir', metavar='DIR', required=True,
                        help='Path to the worktree directory containing docuo.config.*.json files')

    # Options
    parser.add_argument('--record-file', metavar='PATH',
                        default=DEFAULT_RECORD_FILE,
                        help=f'Path to record file (default: {DEFAULT_RECORD_FILE})')

    args = parser.parse_args()

    # Expand and validate worktree_dir
    args.worktree_dir = os.path.abspath(os.path.expanduser(args.worktree_dir))
    if not os.path.isdir(args.worktree_dir):
        parser.error(f'worktree-dir does not exist: {args.worktree_dir}')

    # Default language to zh if not specified (for --get and --update)
    if args.language is None:
        args.language = 'zh'

    if args.count:
        handle_count(args)
    elif args.get is not None:
        handle_get(args)
    elif args.update:
        handle_update(args)
    elif args.init:
        handle_init(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
