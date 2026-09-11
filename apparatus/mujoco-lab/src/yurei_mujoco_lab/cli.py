import argparse, json
from pathlib import Path
from .simulate import POLICIES, simulate_policy, simulate_sequence
from .transitions import calibration_report

def main() -> None:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    run=sub.add_parser("simulate"); run.add_argument("--policy",choices=[*POLICIES,"all"],default="all")
    run.add_argument("--output",type=Path,required=True); run.add_argument("--seconds",type=float,default=20)
    transition=sub.add_parser("calibrate-transitions")
    transition.add_argument("--output",type=Path,required=True)
    transition.add_argument("--replay-output",type=Path)
    a=p.parse_args()
    if a.command == "simulate":
        names=POLICIES if a.policy=="all" else [a.policy]
        result={"format":"yurei-mujoco-lab.replay-set","version":1,
                "replays":[simulate_policy(name,seconds=a.seconds) for name in names]}
    else:
        result=calibration_report()
        if a.replay_output:
            replay={"format":"yurei-mujoco-lab.replay-set","version":1,
                    "replays":[simulate_sequence(result["phases"])]}
            a.replay_output.parent.mkdir(parents=True,exist_ok=True)
            a.replay_output.write_text(json.dumps(replay,indent=2)+"\n")
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2)+"\n")
