#!/usr/bin/env python3
"""Verifica un archivo específico para contar ocurrencias"""

from pathlib import Path
import re

# Archivos con 3 ocurrencias según el reporte
files_to_check = [
    "19676249-ae9c-42af-be2d-b1445b091978.txt",
    "71237a0b-51e1-4cf1-8b11-77fff530ec06.txt",
    "82f5e8f4-c60e-4bc1-9ff4-e781b569f1d9.txt",
    "977b631e-04be-4f85-96d7-87046dd93bb5.txt",
    "d153c0a4-8236-4de7-891d-eb777dcf84a0.txt",
]

corpus_path = Path("documentos finales corpus")
pattern = re.compile(r'centro de salud los [áa]lamos', re.IGNORECASE)

print("Verificando archivos con 3 ocurrencias:")
print("=" * 80)

for filename in files_to_check:
    file_path = corpus_path / filename
    if file_path.exists():
        try:
            content = file_path.read_text(encoding='utf-8')
            matches = pattern.findall(content)
            print(f"\n{filename}:")
            print(f"  Ocurrencias encontradas: {len(matches)}")
            
            # Mostrar contexto de las ocurrencias
            for i, match in enumerate(matches[:3], 1):
                idx = content.lower().find(match.lower())
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(match) + 50)
                    context = content[start:end].replace('\n', ' ')
                    print(f"  Ocurrencia {i}: ...{context}...")
        except Exception as e:
            print(f"\n{filename}: ERROR - {e}")
    else:
        print(f"\n{filename}: NO ENCONTRADO")


