import importlib.util, unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]/"experiments"/"labnote_007"
SPEC=importlib.util.spec_from_file_location("labnote007_eval",ROOT/"evaluate_subscriptions.py")
MODULE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)

class SubscriptionTests(unittest.TestCase):
    def test_miss_cancels_runtime_owned_subscription(self):
        rows=[{"session_id":"session-00","seed":1,"turn_index":i,"predicted_topic":"software","confidence":.9,
          "reusable":flag,"profitable":flag,"net_saved_ms":10 if flag else 0,"speculative_ms":5} for i,flag in enumerate((False,False,True))]
        decisions={("session-00",0,1):{"subscribe":True,"ttl_turns":3,"topic_scope":"software","reason":"test"}}
        result=MODULE.simulate(rows,decisions,0)
        self.assertEqual(result["coverage"],1/3)
        self.assertEqual(result["cancellations"]["miss"],1)

if __name__=="__main__": unittest.main()
