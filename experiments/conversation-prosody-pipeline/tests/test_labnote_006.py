import importlib.util, unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]/"experiments"/"labnote_006"
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
CORPUS=load("labnote006_corpus","corpus.py"); ANALYZE=load("labnote006_analyze","analyze.py")

class Labnote006Tests(unittest.TestCase):
    def test_sessions_and_turns_are_balanced(self):
        sessions=CORPUS.build_corpus(); self.assertEqual(len(sessions),40)
        self.assertTrue(all(len(session["turns"])==25 for session in sessions))
        self.assertEqual(sum(not session["stable"] for session in sessions),10)
    def test_reversals_change_endpoint(self):
        for session in CORPUS.build_corpus():
            self.assertEqual(sum(turn["reversal"] for turn in session["turns"]),5)
    def test_logistic_score_is_bounded(self):
        rows=[{"features":[0,0],"profitable":0},{"features":[1,1],"profitable":1}]
        model=ANALYZE.fit_logistic(rows,epochs=20)
        self.assertTrue(0<=ANALYZE.score(model,[.5,.5])<=1)

if __name__=="__main__": unittest.main()
