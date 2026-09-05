import importlib.util, unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]/"experiments"/"labnote_007"
SPEC=importlib.util.spec_from_file_location("labnote007_structure",ROOT/"analyze_structure.py")
MODULE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)

class Labnote007Tests(unittest.TestCase):
    def test_development_split_and_proceed_rule(self):
        rows=[]
        for session in range(40):
            for index,flag in enumerate((False,True,True,False)):
                rows.append({"session_id":f"session-{session:02d}","session_number":session,
                  "turn_index":index,"seed":101,"profitable":flag,"net_saved_ms":1 if flag else 0,
                  "speculative_ms":1,"stable":True})
        result=MODULE.analyze(rows,"development")
        self.assertEqual(result["sequences"],30)
        self.assertTrue(result["proceed_to_llm_subscription_selector"])
        self.assertGreaterEqual(result["positive_share_in_runs_of_two_or_more"],.25)

if __name__=="__main__": unittest.main()
