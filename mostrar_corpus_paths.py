#!/usr/bin/env python3
"""Muestra las rutas del corpus configuradas en el proyecto"""

from pathlib import Path

print("=" * 80)
print("RUTAS DEL CORPUS CONFIGURADAS EN EL PROYECTO")
print("=" * 80)

# Rutas desde count_centro_salud_alamos.py
print("\n1. Rutas en count_centro_salud_alamos.py (en orden de prioridad):")
possible_paths = [
    Path("corpus_repo/corpus_v1/documents"),
    Path("documentos finales corpus"),
    Path("C:/Users/Usuario/Anonimization_research/documentos finales corpus"),
    Path("corpus_repo/corpus/documents"),
    Path("corpus/documents"),
]

for i, path in enumerate(possible_paths, 1):
    exists = path.exists()
    status = "[EXISTE]" if exists else "[NO EXISTE]"
    print(f"   {i}. {path}")
    print(f"      Ruta absoluta: {path.absolute()}")
    print(f"      Estado: {status}")
    if exists:
        txt_count = len(list(path.glob("*.txt"))) if path.is_dir() else 0
        print(f"      Archivos .txt: {txt_count}")
    print()

# Rutas absolutas disponibles
print("\n2. Rutas absolutas disponibles:")
abs_paths = [
    Path("C:/Users/Usuario/Anonimization_research/corpus_repo/corpus_v1/documents"),
    Path("C:/Users/Usuario/Anonimization_research/corpus_repo/corpus/documents"),
    Path("C:/Users/Usuario/Anonimization_research/documentos finales corpus"),
]

for path in abs_paths:
    exists = path.exists()
    status = "[EXISTE]" if exists else "[NO EXISTE]"
    print(f"   - {path}")
    print(f"     Estado: {status}")
    if exists:
        txt_count = len(list(path.glob("*.txt"))) if path.is_dir() else 0
        print(f"     Archivos .txt: {txt_count}")
    print()

# Ruta que se está usando actualmente
print("\n3. Ruta que se está usando actualmente:")
current_path = None
for path in possible_paths:
    if path.exists():
        current_path = path
        break

if current_path:
    print(f"   [ACTIVA] {current_path.absolute()}")
    print(f"     Esta es la ruta que usa el script por defecto")
else:
    print("   [ERROR] No se encontro ninguna ruta valida")

print("\n" + "=" * 80)

