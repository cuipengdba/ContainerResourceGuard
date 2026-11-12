"""Test-only keepalive around the existing, independently bounded PG probe.

The caller owns both the pressure pipe and its pulse callback. Only the original
SQL call runs on another thread; no parallel pipe readers, process signals,
resource writes, SQL retries, or business deadline changes are introduced.
"""
import threading
import time


class Rejected(Exception):
    pass


def call_with_lease(call, pulse, record):
    outcome = {}
    finished = threading.Event()
    entered = time.monotonic()
    record.update(phase='running', source_SQL_timeout_seconds=30,
                  SQL_completion_observation_deadline_seconds=31, pulse_count=0,
                  pipe_readers_and_writers='calling-thread-only',
                  SQL_retries=0, business_process_signals=0)

    def invoke():
        try:
            outcome['value'] = call()
        except BaseException as error:
            outcome['error'] = error
        finally:
            finished.set()

    worker = threading.Thread(target=invoke, name='crg-test-PG-identity', daemon=True)
    worker.start()
    pulse_error = None
    try:
        while not finished.wait(.25):
            if time.monotonic()-entered > 31:
                raise Rejected('ORIGINAL_SQL_PROBE_DID_NOT_FINISH_WITHIN_31S')
            if pulse_error is None:
                try:
                    pulse()
                    record['pulse_count'] += 1
                except BaseException as error:
                    # Let the already bounded SQL call finish; retain its own
                    # failure if both SQL and keepalive fail. No SQL retry.
                    pulse_error = error
                    record['pulse_error_class'] = type(error).__name__
        worker.join(.1)
        if 'error' in outcome:
            raise outcome['error']
        if pulse_error is not None:
            raise pulse_error
        record['phase'] = 'completed'
        return outcome['value']
    except BaseException as error:
        record.update(phase='failed', primary_error_class=type(error).__name__)
        raise
    finally:
        record.update(elapsed_seconds=time.monotonic()-entered,
                      original_SQL_call_finished=finished.is_set(),
                      SQL_thread_alive_at_return=worker.is_alive())
