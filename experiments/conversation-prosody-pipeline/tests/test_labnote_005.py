import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]/"experiments"/"labnote_005"
SPEC=importlib.util.spec_from_file_location("labnote_005_corpus",ROOT/"corpus.py")
CORPUS=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(CORPUS)
ARCHETYPES,build_corpus=CORPUS.ARCHETYPES,CORPUS.build_corpus

RUN_SPEC=importlib.util.spec_from_file_location("labnote_005_downstream",ROOT/"run_downstream.py")
RUN=importlib.util.module_from_spec(RUN_SPEC); RUN_SPEC.loader.exec_module(RUN)

class CorpusTests(unittest.TestCase):
    def test_balanced_corpus(self):
        turns=build_corpus(); self.assertEqual(len(turns),200)
        self.assertEqual({a:sum(t['archetype']==a for t in turns) for a in ARCHETYPES},{a:40 for a in ARCHETYPES})
    def test_snapshots_are_incremental(self):
        for turn in build_corpus():
            self.assertEqual(len(turn['snapshots']),4)
            self.assertEqual(turn['snapshots'][-1]['time_ms'],turn['true_turn_end_ms'])
            self.assertIn(turn['safe_semantic_commit_snapshot'],range(4))

    def test_private_branch_threshold_is_independent(self):
        predictions={i:{"intent":"unknown","topic":"unknown","branch_confidence":.1} for i in range(4)}
        predictions[1]={"intent":"request_guidance","topic":"software","branch_confidence":.5}
        self.assertEqual(RUN.first_branch(predictions),1)

    def test_source_prediction_ledger_can_be_opened_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"ledger.sqlite3"
            db=sqlite3.connect(path); db.execute("CREATE TABLE marker(value TEXT)"); db.commit(); db.close()
            source=sqlite3.connect(f"file:{path}?mode=ro",uri=True)
            self.assertEqual(source.execute("SELECT count(*) FROM marker").fetchone()[0],0)
            with self.assertRaises(sqlite3.OperationalError): source.execute("INSERT INTO marker VALUES('x')")
            source.close()

if __name__=="__main__": unittest.main()
