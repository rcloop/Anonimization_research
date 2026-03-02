# Análisis del Script: step6_2_validation_entities.py

## Resumen Ejecutivo

**¿Funciona?** SÍ, pero con problemas críticos que deben corregirse.

**¿Es correcto?** PARCIALMENTE - tiene buenas prácticas pero también bugs potenciales.

---

## Problemas Críticos

### 1. BUCLE INFINITO POTENCIAL 🔴

**Ubicación:** Función `call_deepseek_to_correct_entity()` - línea ~150

**Problema:**
```python
while True:  # ← Puede ejecutarse infinitamente
    # ... código ...
    if is_unique_enough and jaccard_similarity(new_text, old_text) < 0.6:
        return new_text, attempt + 1
    # Si nunca pasa la validación, nunca sale del bucle
```

**Riesgo:** Si DeepSeek siempre devuelve valores que no pasan la validación (similitud > 0.6 o duplicados), el script se queda atascado.

**Solución:**
```python
MAX_ATTEMPTS = 10
while attempt < MAX_ATTEMPTS:
    # ... código ...
    attempt += 1

# Si falla después de MAX_ATTEMPTS
if attempt >= MAX_ATTEMPTS:
    debug_print(f"Failed after {MAX_ATTEMPTS} attempts, keeping original", "WARN")
    return old_text, MAX_ATTEMPTS
```

---

### 2. REEMPLAZO MÚLTIPLE INCORRECTO 🔴

**Ubicación:** Línea ~220
```python
texto_doc = texto_doc.replace(txt, new_text)
```

**Problema:** Si la misma entidad aparece múltiples veces en el documento, `replace()` reemplazará TODAS las ocurrencias, no solo la sobreexpresada.

**Ejemplo:**
```
Texto: "El paciente Juan Pérez de la calle Juan Pérez tiene..."
Entidad sobreexpresada: "Juan Pérez de la calle Juan Pérez" (primera vez)
Resultado incorrecto: Reemplaza AMBAS ocurrencias de "Juan Pérez"
```

**Solución:**
```python
# Opción 1: Reemplazar solo la primera ocurrencia
texto_doc = texto_doc.replace(txt, new_text, 1)

# Opción 2: Usar posición específica de la entidad en el JSON
# (más preciso pero requiere más código)
```

---

### 3. FALTA DE VALIDACIÓN DE RESPUESTA API 🟡

**Ubicación:** Línea ~140
```python
new_text = resp_json['choices'][0]['message']['content'].strip()
```

**Problema:** Si la API devuelve un formato inesperado, puede causar `KeyError` o `IndexError`.

**Solución:**
```python
try:
    if 'choices' in resp_json and len(resp_json['choices']) > 0:
        if 'message' in resp_json['choices'][0]:
            new_text = resp_json['choices'][0]['message']['content'].strip()
        else:
            raise ValueError("Missing 'message' in API response")
    else:
        raise ValueError("Missing 'choices' in API response")
except (KeyError, IndexError, ValueError) as e:
    debug_print(f"API response error: {e}", "ERROR")
    continue  # Reintentar
```

---

## Problemas Menores

### 4. Rutas Hardcodeadas 🟡

**Problema:**
```python
entities_dir = Path("corpus/entidades")
docs_dir = Path("corpus/documents")
```

**Solución:** Usar argumentos de línea de comandos:
```python
parser.add_argument("--entities_dir", default="corpus/entidades")
parser.add_argument("--docs_dir", default="corpus/documents")
```

### 5. Sin Límite de Costo API 🟡

**Problema:** No hay control de cuántas llamadas a DeepSeek se hacen, lo que puede resultar en costos inesperados.

**Solución:** Agregar límite de presupuesto o estimación de costo.

---

## Aspectos Correctos ✅

1. **Procesamiento asíncrono:** Usa `asyncio` correctamente
2. **Control de concurrencia:** Semáforo limita a 5 tareas concurrentes
3. **Batches:** Procesa en chunks de 20 para evitar saturar la API
4. **Validación de unicidad:** Usa Jaccard similarity para evitar duplicados
5. **Diccionario global:** Mantiene entidades usadas para evitar colisiones
6. **Diversidad:** Alterna prompts y temperatura para generar variaciones
7. **Métricas:** Guarda estadísticas de corrección
8. **Manejo de errores:** Tiene try-except para errores de API

---

## Recomendaciones

### Antes de usar en producción:

1. **AGREGAR límite máximo de intentos** en `call_deepseek_to_correct_entity()`
2. **CORREGIR reemplazo múltiple** usando `replace(..., 1)` o posición específica
3. **VALIDAR estructura de respuesta** de la API antes de acceder
4. **AGREGAR argumentos de línea de comandos** para rutas configurables
5. **AGREGAR logging** más detallado para debugging
6. **AGREGAR límite de costo** o estimación de presupuesto

---

## Conclusión

**El script FUNCIONA** pero tiene bugs que pueden causar:
- Bucles infinitos en casos edge
- Reemplazos incorrectos en documentos con entidades duplicadas
- Crashes si la API cambia su formato

**Recomendación:** Corregir los 3 problemas críticos antes de usar en producción. Los problemas menores pueden corregirse después.

**Enlace al script original:**
https://github.com/ramsestein/generate_corpus_anonimizacion/blob/main/src/pipeline/step6_2_validation_entities.py


