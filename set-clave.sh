#!/usr/bin/env bash
# Cambia la clave de acceso de index.html (guarda solo su SHA-256).
set -euo pipefail
cd "$(dirname "$0")"
read -rsp "Nueva clave: " c1; echo
read -rsp "Repetila: " c2; echo
[ "$c1" = "$c2" ] || { echo "No coinciden."; exit 1; }
[ -n "$c1" ] || { echo "La clave no puede estar vacía."; exit 1; }
h=$(printf '%s' "papapresupuestos:$c1" | sha256sum | cut -d' ' -f1)
sed -i -E "s/const HASH_CLAVE = \"[^\"]*\";/const HASH_CLAVE = \"$h\";/" index.html
echo "Clave actualizada."
