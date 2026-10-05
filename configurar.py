#!/usr/bin/env python3
"""Configura el acceso de index.html: clave + Upstash Redis (cifrados) y número inicial.

Uso:  python3 configurar.py
La URL y el token se cifran con la clave (PBKDF2-SHA256 + AES-GCM) y se escriben
en la constante ACCESO de index.html. Nada se muestra en pantalla.
"""
import base64
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

CONTADOR = "presupuestos:numero"
ITERACIONES = 250_000
HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


def redis(url, token, *partes):
    ruta = "/".join(urllib.parse.quote(str(p), safe="") for p in partes)
    req = urllib.request.Request(f"{url.rstrip('/')}/{ruta}", method="POST",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r).get("result")


def b64(b):
    return base64.b64encode(b).decode()


def main():
    clave = getpass.getpass("Clave para entrar a la página: ")
    if not clave or clave != getpass.getpass("Repetila: "):
        sys.exit("Las claves no coinciden o están vacías.")
    url = getpass.getpass("UPSTASH_REDIS_REST_URL (no se muestra): ").strip()
    token = getpass.getpass("UPSTASH_REDIS_REST_TOKEN (no se muestra): ").strip()

    try:
        actual = int(redis(url, token, "get", CONTADOR) or 0)
    except (urllib.error.URLError, ValueError) as e:
        sys.exit(f"No pude conectarme a Upstash con esa URL/token: {e}")
    print(f"Conexión OK. Próximo número de presupuesto: {actual + 1}")

    nuevo = input("¿Desde qué número arrancan? (Enter para dejarlo así): ").strip()
    if nuevo:
        if not nuevo.isdigit() or int(nuevo) < 1:
            sys.exit("Tiene que ser un número mayor a 0.")
        redis(url, token, "set", CONTADOR, int(nuevo) - 1)
        print(f"Listo: el próximo presupuesto va a ser el N° {nuevo}")

    salt, iv = os.urandom(16), os.urandom(12)
    llave = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=ITERACIONES).derive(clave.encode())
    datos = AESGCM(llave).encrypt(iv, json.dumps({"url": url, "token": token}).encode(), None)
    acceso = json.dumps({"salt": b64(salt), "iv": b64(iv), "iter": ITERACIONES, "datos": b64(datos)})

    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    html, n = re.subn(r"const ACCESO = .*?;\n", lambda _: f"const ACCESO = {acceso};\n", html, count=1)
    if n != 1:
        sys.exit("No encontré 'const ACCESO' en index.html")
    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("Acceso guardado en index.html. Ahora hay que hacer commit y push.")


if __name__ == "__main__":
    main()
