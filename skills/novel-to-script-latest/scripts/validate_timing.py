#!/usr/bin/env python3
"""Check storyboard structure and exact Decimal timing. No third-party packages."""
import argparse
import re
import sys
from decimal import Decimal
from pathlib import Path

NUMBER = r"\d+(?:\.\d+)?"
PARAGRAPH = re.compile(rf"^段落(\d+)\s*[｜|]\s*总时长[：:]\s*({NUMBER})s\s*$")
SHOT = re.compile(rf"^镜(\d+)\s*[｜|]\s*({NUMBER})s\s*[｜|]\s*(.+)$")


def validate(text, start_shot=1, strict_last=False):
    errors, paragraphs = [], []
    current = None
    next_shot = start_shot
    separator_pending = False
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        paragraph = PARAGRAPH.fullmatch(line)
        shot = SHOT.fullmatch(line)
        if paragraph:
            number, seconds = int(paragraph[1]), Decimal(paragraph[2])
            if current is not None:
                if not separator_pending:
                    errors.append(f"Line {line_number}: missing standalone @ between paragraphs")
                if number != current['number'] + 1:
                    errors.append(f"Line {line_number}: paragraph numbers are not consecutive")
            elif separator_pending:
                errors.append(f"Line {line_number}: unexpected opening @")
            current = {'number': number, 'seconds': seconds, 'shots': []}
            paragraphs.append(current)
            separator_pending = False
        elif line == '@':
            if current is None or separator_pending:
                errors.append(f"Line {line_number}: unexpected or duplicate @")
            separator_pending = True
        elif shot:
            if current is None or separator_pending:
                errors.append(f"Line {line_number}: shot outside a paragraph")
                continue
            number, seconds = int(shot[1]), Decimal(shot[2])
            if number != next_shot:
                errors.append(f"Line {line_number}: expected shot {next_shot}, found {number}")
            next_shot = number + 1
            if seconds <= 0:
                errors.append(f"Line {line_number}: shot duration must be positive")
            if len(shot[3].split('/')) != 3 or any(not x.strip() for x in shot[3].split('/')):
                errors.append(f"Line {line_number}: expected three shot labels separated by /")
            current['shots'].append(seconds)
        elif re.match(r'^段落\d', line) or re.match(r'^镜\d', line):
            errors.append(f"Line {line_number}: malformed paragraph or shot heading")
        elif separator_pending:
            errors.append(f"Line {line_number}: content after @ must begin a new paragraph")
    if not paragraphs:
        errors.append('No paragraphs found')
    if separator_pending:
        errors.append('Trailing @ is not a between-paragraph separator')
    for index, paragraph in enumerate(paragraphs):
        total = sum(paragraph['shots'], Decimal('0'))
        label = f"Paragraph {paragraph['number']}"
        if not paragraph['shots']:
            errors.append(f"{label}: no shots found")
        if paragraph['seconds'] <= 0:
            errors.append(f"{label}: paragraph duration must be positive")
        if total != paragraph['seconds']:
            errors.append(f"{label}: declared {paragraph['seconds']}s, shots sum to {total}s")
        if strict_last or index != len(paragraphs) - 1:
            if not Decimal('12.0') <= total <= Decimal('15.0'):
                errors.append(f"{label}: {total}s is outside 12.0-15.0s")
    return errors, paragraphs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path, help='UTF-8 storyboard text file')
    parser.add_argument('--start-shot', type=int, default=1)
    parser.add_argument('--strict-last', action='store_true')
    args = parser.parse_args()
    if args.start_shot < 1:
        parser.error('--start-shot must be at least 1')
    try:
        text = args.file.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError) as exc:
        parser.exit(2, f'Cannot read input: {exc}\n')
    errors, paragraphs = validate(text, args.start_shot, args.strict_last)
    if errors:
        for error in errors:
            print('ERROR:', error)
        return 1
    shots = sum(len(p['shots']) for p in paragraphs)
    total = sum((p['seconds'] for p in paragraphs), Decimal('0'))
    print(f'PASS: {len(paragraphs)} paragraphs, {shots} shots, {total}s')
    print('Structure and timing only; review dialogue pacing, coverage, and continuity separately.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
