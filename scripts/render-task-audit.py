#!/usr/bin/env python3
"""Render the human task table from the current per-task acceptance records."""
import argparse,json
from pathlib import Path

LABELS={
    'complete-in-defined-scope':'本项完成',
    'partial-evidence-or-verification-open':'已有部分证据/仍待闭环',
    'superseded-by-three-resource-request':'按三资源需求取消',
    'waiting-real-duration-and-postflight':'待真实时长/后续验收',
    'waiting-unavailable-hardware':'缺目标硬件',
    'partly-superseded-with-retained-work':'部分取消/仍有待办',
}

def render(directory):
    audit=json.loads((directory/'current-52-task-audit.json').read_bytes())
    registry=json.loads((directory/'current-task-registry.json').read_bytes())
    tasks=audit['tasks']; assert len(tasks)==52 and len({t['id'] for t in tasks})==52
    completed=sum(t['completion_claim'] for t in tasks)
    assert completed==audit['completed_in_defined_scope'] and 0<=completed<=52
    release='稳定1.0已按当前记录接受' if audit['stable_release_accepted'] else '稳定1.0尚未接受'
    byid={t['id']:t for t in registry['tasks']}; assert len(byid)==52
    def cell(value):
        assert isinstance(value,str)
        return value.replace('|','&#124;').replace('\r\n','<br>').replace('\n','<br>')
    lines=['# 原52项任务逐项审核','',
        f'本页由当前[逐项机器审核](current-52-task-audit.json)和[完整登记](current-task-registry.json)生成；{completed}项按各自原定义范围完成，{release}。所有原定义、失败和历史仍保留，不因新增测试缩减任务。','',
        '每行完整反映当前已验证范围和仍需完成的条件；实际运行、模拟输入、原路径业务与长期证据不能混用。默认20%完整业务失败不能由manual参考通过覆盖。','',
        '[此前Markdown审核快照](current-52-task-audit-before-three-resource-persistence.md)保留原字节；后续证据已同步到下表。','',
        '| 任务 | 本项状态 | 已验证范围 | 仍需完成或边界 |',
        '| --- | --- | --- | --- |']
    for t in tasks:
        source=byid[t['id']]; acceptance=source['current_acceptance']
        assert source['completion_claim']==t['completion_claim']
        assert source['archived_definition']==t['archived_definition']
        assert all(acceptance[k]==t[k] for k in ('verified_scope','remaining_or_boundary','evidence'))
        evidence=Path(t['evidence']); assert not evidence.is_absolute() and '..' not in evidence.parts and (directory/evidence).is_file()
        lines.append('| '+cell(t['id'])+' | '+LABELS[t['current_status']]+' | '+cell(t['verified_scope'])+' | '+cell(t['remaining_or_boundary'])+' [证据]('+evidence.as_posix()+') |')
    lines+=['','本表不自动宣布任务完成。改动验收结论须先更新并核对当前登记与逐项机器审核；所有原任务定义继续通过登记中的归档来源追溯。','']
    return '\n'.join(lines).encode('utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docs',type=Path,default=Path(__file__).resolve().parent.parent/'docs')
    parser.add_argument('--check',action='store_true',help='compare without writing')
    args=parser.parse_args(); value=render(args.docs)
    target=args.docs/'current-52-task-audit.md'
    if args.check:
        if target.read_bytes()!=value:parser.exit(1,'task Markdown is stale; regenerate from the current audit records\n')
    else:target.write_bytes(value)
