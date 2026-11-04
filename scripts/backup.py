"""SQLite online backup/restore, including validation before replacing an inactive DB."""
import argparse
import sqlite3
from pathlib import Path


def backup(source,destination):
    source=Path(source).resolve()
    destination=Path(destination).resolve()
    if source==destination or not source.is_file() or destination.exists():
        raise ValueError('Source must exist; destination must be new and distinct.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(destination) as dst:
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or src.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Invalid source database.')
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Backup validation failed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Backup or restore to a NEW database path. Stop app before restoring.')
    parser.add_argument('source')
    parser.add_argument('destination')
    args=parser.parse_args()
    backup(args.source,args.destination)
    print('Backup validated. For restore, point DATABASE at the new destination before starting app.')
