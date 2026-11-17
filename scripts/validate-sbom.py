#!/usr/bin/env python3
"""Validate an SBOM with pinned local official schemas; no network retrieval.

Optional development tool: jsonschema==4.26.0 in a separate tools environment.
Neither jsonschema nor its dependencies are shipped in the CRG executable.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('SBOM',type=Path)
p.add_argument('--schema-directory',type=Path,required=True)
a=p.parse_args()
try:
    import jsonschema
    from referencing import Registry,Resource
    from referencing.jsonschema import DRAFT7
    if importlib.metadata.version('jsonschema')!='4.26.0':p.error('use jsonschema==4.26.0 in a separate development environment')
except ImportError:
    p.error('optional jsonschema==4.26.0 tool missing; the CRG runtime does not need it')
lock=json.loads(Path(__file__).with_name('sbom-schema-lock.json').read_text(encoding='utf-8'))
resources=[];schemas={}
try:
    for name,expected in lock['files'].items():
        path=a.schema_directory/name
        if path.stat().st_size>4*1024**2:raise ValueError('schema exceeds 4MiB')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('official schema digest mismatch: '+name)
        schema=json.loads(data);schemas[name]=schema
        resource=Resource.from_contents(schema,default_specification=DRAFT7)
        for uri in ['http://cyclonedx.org/schema/'+name,'https://cyclonedx.org/schema/'+name,'https://raw.githubusercontent.com/CycloneDX/specification/1.6/schema/'+name]:resources.append((uri,resource))
    if a.SBOM.stat().st_size>2*1024**2:raise ValueError('SBOM exceeds 2MiB')
    bom=json.loads(a.SBOM.read_bytes())
    validator=jsonschema.Draft7Validator(schemas['bom-1.6.schema.json'],registry=Registry().with_resources(resources),format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)
    errors=[{'path':'/'.join(map(str,e.path)),'message':e.message} for e in validator.iter_errors(bom)]
    print(json.dumps({'schema_valid':not errors,'SBOM_sha256':hashlib.sha256(a.SBOM.read_bytes()).hexdigest(),'validator':'jsonschema 4.26.0 / Draft7Validator','errors':errors,'scope':'schema validation only; not completeness, provenance or security certification'}))
    p.exit(1 if errors else 0)
except (ValueError,OSError) as error:
    p.exit(1,str(error)+'\n')
