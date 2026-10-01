"""Ledger structure and current-candidate semantics, independent of total count."""
import collections
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_check_updates import MONITOR as M


class ClaimsLedgerTests(unittest.TestCase):
    def test_every_claim_is_in_a_seven_column_gfm_table(self):
        lines = Path(M.CLAIMS_PATH).read_text(encoding='utf-8').split('\n')
        ids = []
        for i, line in enumerate(lines):
            if not line.startswith('| C-'):
                continue
            with self.subTest(line=i+1):
                row = M.CLAIM_ROW_RE.fullmatch(line)
                self.assertIsNotNone(row)
                self.assertEqual(7,len(line.strip('|').split('|')))
                ids.append(row[1])
                j=i-1
                while j>=0 and lines[j].startswith('| C-'): j-=1
                self.assertGreaterEqual(j,1)
                self.assertEqual(['ID','路徑','主張','依據','取證日','版本','狀態'],
                                 [c.strip() for c in lines[j-1].strip('|').split('|')])
                self.assertTrue(all(re.fullmatch(r':?-+:?',c.strip()) for c in lines[j].strip('|').split('|')))
        self.assertEqual(len(ids),len(set(ids)))
        self.assertGreater(len(ids),0)

    def test_summary_counts_derive_from_existing_rows(self):
        text=Path(M.CLAIMS_PATH).read_text(encoding='utf-8')
        rows=M.CLAIM_ROW_RE.findall(text)
        counts=collections.Counter('被取代' if r[-1].startswith('被取代') else r[-1] for r in rows)
        for status,count in counts.items():
            self.assertRegex(text,rf'\| {status} \| {count} \|')
        self.assertIn(f'| **總計** | **{len(rows)}** |',text)

    def test_explicit_status_contract_keeps_uncertain_and_negative_claims(self):
        for status,active in [('被取代',False),('被取代→C-123',False),('被取代 → C-456',False),
                              ('移出範圍',False),('有疑',True),('已驗證',True),('結構性',True)]:
            row=f'| C-900 | `.agents/probe.json` | 官方不讀 | 文件 | 2026-10-01 | v1 | {status} |\n'
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'claims.md';path.write_text(row,encoding='utf-8')
                with mock.patch.object(M,'CLAIMS_PATH',str(path)): claims=M.load_claims()
                self.assertEqual(active,bool(claims))
                self.assertEqual(active,bool(M.claims_for_token('.agents/probe.json',claims)))

    def test_real_current_hits_preserve_successors_and_uncertain_entry(self):
        claims=M.load_claims();by_id={c['id']:c for c in claims}
        for retired in ('C-41','C-42','C-47','C-48','C-81','C-117'):
            self.assertNotIn(retired,by_id)
        for active in ('C-110','C-111','C-114','C-115','C-116'):
            self.assertIn(active,by_id)
        for token,needed in [('.agents/AGENTS.md','C-115'),('~/.gemini/config/skills/','C-110'),
                             ('~/.gemini/antigravity/skills/','C-111')]:
            hits={c['id'] for c in M.claims_for_token(token,claims)}
            self.assertIn(needed,hits)
            self.assertFalse(hits & {'C-41','C-42','C-47','C-48','C-81'})

    def test_policy_examples_are_preserved_but_not_external_path_claims(self):
        rows={r[0]:r for r in M.CLAIM_ROW_RE.findall(Path(M.CLAIMS_PATH).read_text(encoding='utf-8'))}
        policy=rows['C-117']
        self.assertEqual([],M._claim_paths(policy[1]))
        self.assertIn('apps/web/.agents/ORIGINAL_REQUEST.md',policy[2])
        self.assertIn('apps/web/.agents/x/ORIGINAL_REQUEST.md',policy[2])
        # Historical evidence remains in the ledger even though matching skips it.
        self.assertEqual('被取代→C-110',rows['C-47'][-1])
