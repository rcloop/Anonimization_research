#!/usr/bin/env python3
"""
Script para contar cuántas veces aparece "centro de salud los alamos" en el corpus.
"""

import os
from pathlib import Path
import re

def count_centro_salud_alamos(corpus_path):
    """Cuenta las ocurrencias de 'centro de salud los alamos' en el corpus."""
    
    # Patrón único case-insensitive que cubre todas las variantes (con y sin acentos)
    # Usamos un solo patrón para evitar contar múltiples veces la misma ocurrencia
    pattern = re.compile(r'centro de salud los [áa]lamos', re.IGNORECASE)
    
    total_count = 0
    files_with_match = []
    
    corpus_dir = Path(corpus_path)
    
    if not corpus_dir.exists():
        print(f"[ERROR] El directorio no existe: {corpus_path}")
        return
    
    txt_files = list(corpus_dir.glob("*.txt"))
    print(f"Buscando en {len(txt_files)} archivos en: {corpus_path}")
    print("=" * 80)
    
    for txt_file in txt_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Contar ocurrencias (solo una vez por ocurrencia real)
            matches = pattern.findall(content)
            file_count = len(matches)
            
            if file_count > 0:
                total_count += file_count
                files_with_match.append((txt_file.name, file_count))
                
        except Exception as e:
            print(f"[WARNING] Error leyendo {txt_file.name}: {e}")
    
    print(f"\n[RESULTADO] Total de ocurrencias encontradas: {total_count}")
    print(f"Archivos que contienen la frase: {len(files_with_match)}")
    
    if files_with_match:
        print("\nArchivos con ocurrencias:")
        for filename, count in files_with_match[:20]:  # Mostrar primeros 20
            print(f"  - {filename}: {count} ocurrencia(s)")
        if len(files_with_match) > 20:
            print(f"  ... y {len(files_with_match) - 20} archivo(s) más")
    
    return total_count, files_with_match


if __name__ == "__main__":
    # Buscar en corpus_v1
    possible_paths = [
        Path("corpus_repo/corpus_v1/documents"),
        Path("documentos finales corpus"),
        Path("C:/Users/Usuario/Anonimization_research/documentos finales corpus"),
        Path("corpus_repo/corpus/documents"),
        Path("corpus/documents"),
    ]
    
    corpus_path = None
    for path in possible_paths:
        if path.exists():
            corpus_path = path
            break
    
    if corpus_path:
        print(f"[INFO] Usando corpus en: {corpus_path.absolute()}\n")
        total_count, files_with_match = count_centro_salud_alamos(corpus_path)
        
        # Guardar resultados detallados en un archivo
        if files_with_match:
            output_file = Path("resultados_centro_salud_alamos.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("RESULTADOS DETALLADOS: Centro de Salud Los Alamos\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Total de ocurrencias: {total_count}\n")
                f.write(f"Archivos con ocurrencias: {len(files_with_match)}\n\n")
                f.write("Detalle por archivo:\n")
                f.write("-" * 80 + "\n")
                for filename, count in sorted(files_with_match, key=lambda x: x[1], reverse=True):
                    f.write(f"{filename}: {count} ocurrencia(s)\n")
            print(f"\n[INFO] Resultados detallados guardados en: {output_file.absolute()}")
    else:
        print("[ERROR] No se encontró el directorio del corpus.")
        print("\nUbicaciones buscadas:")
        for path in possible_paths:
            print(f"  - {path}")
        print("\nPor favor, especifica la ruta correcta del corpus.")

