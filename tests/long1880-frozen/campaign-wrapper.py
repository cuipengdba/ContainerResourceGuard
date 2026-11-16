from pathlib import Path
import hashlib,runpy,signal,sys
w=Path(__file__).resolve().parent;tool=w/'tests/vendor-soak-campaign.py'
assert hashlib.sha256(tool.read_bytes()).hexdigest()=='a89ed2e32fe02876c39a240f8368eecb964ff7bce02235072ab417760fe282ce'
def stopped(signum,frame):raise KeyboardInterrupt('test coordinator stop requested')
signal.signal(signal.SIGTERM,stopped)
sys.argv=[str(tool),*sys.argv[1:]]
runpy.run_path(str(tool),run_name='__main__')
