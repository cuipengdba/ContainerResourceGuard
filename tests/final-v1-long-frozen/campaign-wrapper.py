from pathlib import Path
import hashlib,runpy,signal,sys
w=Path(__file__).resolve().parent;tool=w/'tests/vendor-soak-campaign.py'
assert hashlib.sha256(tool.read_bytes()).hexdigest()=='d3865c9e2b78140297636fe06e33a6b5235d9c703298043cfe8914d450b32287'
def stopped(signum,frame):raise KeyboardInterrupt('test coordinator stop requested')
signal.signal(signal.SIGTERM,stopped)
sys.argv=[str(tool),*sys.argv[1:]]
runpy.run_path(str(tool),run_name='__main__')
