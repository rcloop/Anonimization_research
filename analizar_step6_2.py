#!/usr/bin/env python3
"""
Análisis del script step6_2_validation_entities.py
"""

print("=" * 80)
print("ANÁLISIS DEL SCRIPT: step6_2_validation_entities.py")
print("=" * 80)

issues = []
warnings = []
good_practices = []

# 1. ANÁLISIS DE FUNCIONALIDAD
print("\n1. FUNCIONALIDAD GENERAL:")
print("-" * 80)
print("✓ Detecta entidades sobreexpresadas (muy largas)")
print("✓ Usa DeepSeek API para generar correcciones")
print("✓ Actualiza archivos JSON y TXT")
print("✓ Procesamiento asíncrono con batches")

# 2. PROBLEMAS IDENTIFICADOS
print("\n2. PROBLEMAS Y ADVERTENCIAS:")
print("-" * 80)

issues.append({
    "severity": "HIGH",
    "issue": "Bucle infinito potencial en call_deepseek_to_correct_entity",
    "location": "Línea ~150",
    "description": "El bucle 'while True' puede ejecutarse indefinidamente si DeepSeek siempre devuelve valores rechazados",
    "fix": "Agregar límite máximo de intentos (ej: max_attempts=10)"
})

issues.append({
    "severity": "MEDIUM",
    "issue": "Reemplazo de texto simple puede causar errores",
    "location": "texto_doc.replace(txt, new_text)",
    "description": "Si la entidad aparece múltiples veces, reemplazará TODAS las ocurrencias, no solo la específica",
    "fix": "Usar reemplazo basado en posición o contexto único"
})

issues.append({
    "severity": "MEDIUM",
    "issue": "No hay validación de formato de respuesta de DeepSeek",
    "location": "resp_json['choices'][0]['message']['content']",
    "description": "Si la API devuelve formato inesperado, puede causar KeyError",
    "fix": "Agregar try-except y validación de estructura"
})

issues.append({
    "severity": "LOW",
    "issue": "Rutas hardcodeadas",
    "location": "entities_dir = Path('corpus/entidades')",
    "description": "Las rutas están hardcodeadas, no son configurables",
    "fix": "Usar argumentos de línea de comandos o variables de entorno"
})

warnings.append({
    "type": "PERFORMANCE",
    "issue": "Procesamiento secuencial de chunks",
    "description": "Aunque usa asyncio, procesa chunks de 20 documentos secuencialmente",
    "suggestion": "Podría optimizarse para procesar múltiples chunks en paralelo"
})

warnings.append({
    "type": "COST",
    "issue": "Llamadas API sin límite de costo",
    "description": "No hay control de cuántas llamadas a DeepSeek se hacen",
    "suggestion": "Agregar límite de presupuesto o costo estimado"
})

# 3. ASPECTOS CORRECTOS
print("\n3. ASPECTOS CORRECTOS:")
print("-" * 80)
good_practices.append("✓ Usa asyncio para procesamiento concurrente")
good_practices.append("✓ Implementa semáforo para limitar concurrencia (5)")
good_practices.append("✓ Usa Jaccard similarity para validar diferencias")
good_practices.append("✓ Mantiene diccionario de entidades usadas para evitar duplicados")
good_practices.append("✓ Alterna prompts y temperatura para diversidad")
good_practices.append("✓ Guarda métricas de corrección")
good_practices.append("✓ Maneja errores de API con reintentos")

# 4. PROBLEMAS CRÍTICOS
print("\n4. PROBLEMAS CRÍTICOS QUE DEBEN CORREGIRSE:")
print("-" * 80)

critical_issues = [
    {
        "issue": "BUCLE INFINITO",
        "code": "while True:",
        "problem": "Si DeepSeek siempre devuelve valores rechazados, el script nunca termina",
        "solution": """
async def call_deepseek_to_correct_entity(..., max_attempts: int = 10):
    attempt = 0
    while attempt < max_attempts:  # ← Agregar límite
        # ... código existente ...
        attempt += 1
    
    # Si llegamos aquí, falló después de max_attempts
    debug_print(f"Failed after {max_attempts} attempts", "ERROR")
    return old_text, max_attempts  # Devolver original si falla
"""
    },
    {
        "issue": "REEMPLAZO MÚLTIPLE",
        "code": "texto_doc.replace(txt, new_text)",
        "problem": "Si la misma entidad aparece 2 veces, reemplaza ambas",
        "solution": """
# Usar reemplazo basado en posición o contexto
import re
# Opción 1: Reemplazar solo la primera ocurrencia
texto_doc = texto_doc.replace(txt, new_text, 1)

# Opción 2: Usar regex con contexto único
# (más complejo pero más preciso)
"""
    },
    {
        "issue": "VALIDACIÓN DE API",
        "code": "resp_json['choices'][0]['message']['content']",
        "problem": "Puede fallar si la estructura de respuesta cambia",
        "solution": """
try:
    if 'choices' in resp_json and len(resp_json['choices']) > 0:
        new_text = resp_json['choices'][0]['message']['content'].strip()
    else:
        raise ValueError("Unexpected API response format")
except (KeyError, IndexError) as e:
    debug_print(f"API response error: {e}", "ERROR")
    continue  # Reintentar
"""
    }
]

# 5. IMPRESIÓN DE RESULTADOS
for i, issue in enumerate(issues, 1):
    print(f"\n[{issue['severity']}] {i}. {issue['issue']}")
    print(f"   Ubicación: {issue['location']}")
    print(f"   Descripción: {issue['description']}")
    print(f"   Solución: {issue['fix']}")

print("\n" + "=" * 80)
print("RESUMEN:")
print("=" * 80)
print(f"✓ Aspectos correctos: {len(good_practices)}")
print(f"⚠ Problemas identificados: {len(issues)}")
print(f"⚠ Advertencias: {len(warnings)}")
print(f"🔴 Problemas críticos: {len(critical_issues)}")

print("\nCONCLUSIÓN:")
print("-" * 80)
print("El script FUNCIONA pero tiene problemas que pueden causar:")
print("  1. Bucles infinitos si DeepSeek falla repetidamente")
print("  2. Reemplazos incorrectos si hay entidades duplicadas")
print("  3. Crashes si la API devuelve formato inesperado")
print("\nRECOMENDACIÓN: Corregir los problemas críticos antes de usar en producción")

for practice in good_practices:
    print(f"  {practice}")

print("\n" + "=" * 80)


