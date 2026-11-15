#!/bin/sh
# XDMOD workspace bootstrap (command-layer.md §2).
#
# This file is a COPY of xdmod/templates/bootstrap.sh, kept in the manifest repo as
# scripts/bootstrap.sh (D118). Do not edit the copy: `curatrix check <manifest>` warns when it
# differs from the template (CK-H5).
#
# usage, from the (empty) folder that becomes the workspace root:
#   git clone https://github.com/tiacsys/robarm-manifest
#   robarm-manifest/scripts/bootstrap.sh --role ee
#
# Roles: syseng (default) | ee | ee3d | me | sw | integration | full  (repo-topology.md §4)
# Environment: PYTHON (default python3, >= 3.12), WEST_VERSION (default 1.4.0).
set -eu

ROLE=syseng
while [ $# -gt 0 ]; do
    case "$1" in
        --role) ROLE="$2"; shift 2 ;;
        --role=*) ROLE="${1#--role=}"; shift ;;
        -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
        *) echo "bootstrap.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done

MANIFEST_DIR=$(cd "$(dirname "$0")/.." && pwd)
WS=$(pwd)
case "$MANIFEST_DIR" in
    "$WS"/*) MANIFEST=${MANIFEST_DIR#"$WS"/} ;;
    *) echo "bootstrap.sh: run it from the workspace root, the folder that holds $(basename "$MANIFEST_DIR")/" >&2; exit 2 ;;
esac

# Every tool runs under a memory limit and a timeout (D71). curatrix takes over once installed;
# until then: a systemd user scope if there is one, else timeout + ulimit -v.
lim() {
    mem=$1; t=$2; shift 2
    if command -v systemd-run >/dev/null 2>&1 && systemd-run --user --scope --quiet --collect -- true 2>/dev/null; then
        systemd-run --user --scope --quiet --collect -p MemoryMax="$mem" -p MemorySwapMax=0 -- \
            timeout --kill-after=10s "$t" "$@"
    else
        timeout --kill-after=10s "$t" "$@"
    fi
}

PY=${PYTHON:-python3}
echo "== 1/4 .venv with west"
[ -x .venv/bin/python ] || lim 2G 10m "$PY" -m venv .venv
lim 2G 10m .venv/bin/python -m pip install -q "west==${WEST_VERSION:-1.4.0}"

echo "== 2/4 west init -l $MANIFEST + west update (minimal default groups, D93)"
[ -d .west ] || lim 1G 5m .venv/bin/west init -l "$MANIFEST"
lim 2G 30m .venv/bin/west update

echo "== 3/4 curatrix (editable, from xdmod)"
lim 2G 10m .venv/bin/python -m pip install -q -e xdmod/curatrix

echo "== 4/4 curatrix bootstrap --role $ROLE"
exec .venv/bin/curatrix bootstrap --role "$ROLE"
