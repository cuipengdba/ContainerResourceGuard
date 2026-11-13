#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
crg_version="${1:-dev}"
crg_revision="${CRG_REVISION:-$(git rev-parse HEAD)}"
[[ "$crg_version" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'invalid build version' >&2; exit 1; }
[[ "$crg_revision" =~ ^[0-9a-f]{40}$ ]] && [[ "$crg_revision" == "$(git rev-parse HEAD)" ]] || { echo 'checkout the exact source revision before building' >&2; exit 1; }
export GOTOOLCHAIN=local GOWORK=off GOENV=off GOPROXY=off GOSUMDB=off
export GOFLAGS='' GOEXPERIMENT='' GOAMD64=v1 GOARM64=v8.0
crg_python="${CRG_PYTHON:-python3}"
crg_toolchain="$("$crg_python" -c 'import json; print(json.load(open("scripts/toolchain.json"))["version"])')"
[[ "$(go env GOVERSION)" == "$crg_toolchain" ]] || { echo "release build requires $crg_toolchain" >&2; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'release source must be committed' >&2; exit 1; }
mkdir -p dist
for arch in amd64 arm64; do
  CGO_ENABLED=0 GOOS=linux GOARCH="$arch" go build -trimpath -buildvcs=false \
    -ldflags "-s -w -X main.version=$crg_version -X main.revision=$crg_revision" -o "dist/crg-linux-$arch" ./cmd/crg
done
"$crg_python" scripts/release-metadata.py "$crg_version"
