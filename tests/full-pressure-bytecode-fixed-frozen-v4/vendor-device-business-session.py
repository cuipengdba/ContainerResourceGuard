#!/usr/bin/env python3
"""Pair a frozen thread session with one device session in a test executor.

Device startup/save failure lets the original workload proceed. Final diagnostic
failure remains visible to the test executor; an original business error keeps
its identity. No product startup, resource policy or database command is added.
"""
import hashlib
import importlib.util
from pathlib import Path

SESSION_SHA = '632a93f267bcb8aeee992d00f5fc4f0aaec63e8bbcd5e393ba83bf14b3474444'
path = Path(__file__).with_name('vendor-device-session.py')
if hashlib.sha256(path.read_bytes()).hexdigest() != SESSION_SHA:
    raise ValueError('DEVICE_BUSINESS_FROZEN_SESSION')
spec = importlib.util.spec_from_file_location('device_business_frozen_session', path)
device = importlib.util.module_from_spec(spec)
spec.loader.exec_module(device)


class Session:
    def __init__(self, inner, source, root, label, devices, row, save):
        device.require('device_observer' not in row, 'DEVICE_BUSINESS_SINGLE_SESSION')
        self.inner, self.row, self.save, self.devices = inner, row, save, devices
        self.record = row.setdefault('device_observer', {})
        self.device = device.Session(source, root, label, self.record)
        self.failure, self.attempted, self.finished = None, False, False

    def remember(self, error):
        if self.failure is None:
            self.failure = error
        self.record.setdefault('integration_errors', []).append(str(error) if isinstance(error, device.Rejected) else type(error).__name__)
        self.record['integration_phase'] = 'diagnostic-failed'

    def save_without_interrupting_work(self):
        try:
            self.save()
        except Exception as error:
            self.remember(error)

    def start(self, target, group, duration=900):
        device.require(not self.attempted, 'DEVICE_BUSINESS_SINGLE_START')
        self.attempted = True
        try:
            self.device.start({k: target[k] for k in ['pid', 'start_ticks']}, group, self.devices, duration)
        except Exception as error:
            # Session.start already tries to reap its own partial startup.
            # Diagnostic failure must not skip the original workload.
            self.remember(error)
        self.save_without_interrupting_work()
        self.inner.start(target, group, duration)

    def finish_device(self):
        try:
            self.device.stop()
            if self.failure is not None:
                raise self.failure
            record = self.record
            device.require(record['phase'] == 'collected' and (record['report_phase'] == 'observed'
                           or (record['report_reason'] == 'observer-interrupted' and record['owned_observer_TERM_count'] == 1)),
                           'DEVICE_BUSINESS_DIAGNOSTIC_TERMINAL')
            intervals = list(self.row.get('reload_intervals', []))
            for key in ['engine_interval', 'diagnostic_failed_engine_interval']:
                if key in self.row:
                    intervals.append(self.row[key])
            covered = bool(intervals) and len(intervals) <= 32 and all(
                record['first_sample_epoch'] <= item['started_epoch'] <= item['ended_epoch'] <= record['last_sample_epoch']
                for item in intervals)
            record['engine_and_reload_interval_envelopes_covered'] = covered
            device.require(covered, 'DEVICE_BUSINESS_INTERVAL_ENVELOPE')
            device.require(record['maximum_sample_gap_seconds'] is not None and record['maximum_sample_gap_seconds'] <= 3,
                           'DEVICE_BUSINESS_SAMPLE_GAP')
            record.update(integration_phase='collected-intervals-covered', sampling_gaps_reviewed=True,
                          optional_missing_fields_still_unknown=True, original_business_and_stable_acceptance_proven=False)
        except BaseException as error:
            self.remember(error)
            raise
        finally:
            self.save_without_interrupting_work()
        if self.failure is not None:
            raise self.failure

    def stop(self):
        if self.finished:
            return
        try:
            if self.attempted:
                # Always stop both owned observers, including when the original
                # thread session fails. Its first error cannot be replaced.
                return device.finish_preserving_business(self.inner.stop, self.finish_device, self.remember)
            self.inner.stop()
            self.device.stop()
        finally:
            self.finished = True
