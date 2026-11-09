#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
crg_version="${1:-dev}"
crg_revision="${CRG_REVISION:-$(git rev-parse HEAD)}"
mkdir -p dist
for arch in amd64 arm64; do
  CGO_ENABLED=0 GOOS=linux GOARCH="$arch" go build -trimpath -buildvcs=false \
    -ldflags "-s -w -X main.version=$crg_version -X main.revision=$crg_revision" -o "dist/crg-linux-$arch" ./cmd/crg
done
