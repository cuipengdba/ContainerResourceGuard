"""Draft integration seam around the frozen original pressure business method.

It does not provide a collector factory, change any workload/criteria, or claim
vendor runtime qualification. Ordinary diagnostic failures are recorded while
the original work and its exception object retain precedence.
"""

def preserve_original_business(work, start, finish, record, save):
    record.setdefault('diagnostic_errors', [])

    def error(action, exc):
        record['diagnostic_errors'].append({'action': action, 'error_class': type(exc).__name__})
        record['diagnostic_failed'] = True

    def persist():
        try:
            save()
        except Exception as exc:
            error('save', exc)

    try:
        start()
    except Exception as exc:
        error('start', exc)
    persist()
    try:
        return work()
    except BaseException as exc:
        record['original_business_error_class'] = type(exc).__name__
        raise
    finally:
        try:
            finish()
        except Exception as exc:
            error('finish', exc)
        record['diagnostic_failed'] = bool(record['diagnostic_errors'])
        record['original_business_method_invoked'] = True
        persist()


def install(core, factory):
    cls = core.PressureExecution
    if getattr(cls, '_crg_full_pressure_observer_installed', False):
        raise ValueError('duplicate full-pressure observer installation')
    original = cls.business_native

    def observed(self, role, folder, group, row):
        record = {'phase': 'draft-collector-integration', 'role': role}
        row['full_BPF_diagnostic'] = record
        controller = [None]

        def start():
            controller[0] = factory(self, role, folder, group, row, record)
            controller[0].start()

        def finish():
            if controller[0] is not None:
                controller[0].finish()

        return preserve_original_business(lambda: original(self, role, folder, group, row),
                                          start, finish, record, self.save)

    cls.business_native = observed
    cls._crg_full_pressure_observer_installed = True
    return original
