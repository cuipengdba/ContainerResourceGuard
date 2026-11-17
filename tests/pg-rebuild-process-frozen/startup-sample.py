"""Read mandatory counters; explicitly retain optional PSI unavailability."""
from pathlib import Path
def snapshot(group):
    group=Path(group)
    row={name:(group/name).read_text() for name in ['io.stat','cpu.stat','memory.current']}
    try:row['io.pressure']={'state':'available','exact_utf8':(group/'io.pressure').read_text()}
    except FileNotFoundError:row['io.pressure']={'state':'unavailable','reason':'missing-cgroup-file','error_class':'FileNotFoundError'}
    except PermissionError:row['io.pressure']={'state':'unavailable','reason':'read-denied','error_class':'PermissionError'}
    return row
