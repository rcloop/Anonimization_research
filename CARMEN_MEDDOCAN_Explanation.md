# Explicación: Corpus CARMEN y MEDDOCAN

## Resumen Ejecutivo

**CARMEN** y **MEDDOCAN** son los **dos únicos corpus públicos en español** para entrenar modelos de desidentificación con etiquetas PHI (Protected Health Information).

---

## 📚 MEDDOCAN Corpus

### ¿Qué es MEDDOCAN?

**MEDDOCAN** (Medical Document Anonymization) es el **primer corpus a gran escala en español** específicamente diseñado para desidentificación de documentos médicos.

### Características Principales

| Característica | Detalle |
|----------------|---------|
| **Documentos** | ~1,000 casos clínicos |
| **División** | Training: 500<br>Development: 250<br>Test: 250 |
| **Entidades PHI** | **22,795 entidades** anotadas |
| **Densidad** | ~22.8 entidades por documento |
| **Esquema de etiquetado** | IOB2 (Inside-Outside-Beginning) |
| **Calidad** | Anotaciones expertas, alta calidad |
| **Disponibilidad** | ✅ Público |
| **Fuente** | meddocan.github.io |

### Tipos de Entidades PHI en MEDDOCAN

MEDDOCAN anota los siguientes tipos de PHI:

- **NOMBRE_SUJETO_ASISTENCIA** (Nombres de pacientes)
- **FECHA** (Fechas de nacimiento, fechas de eventos)
- **TERRITORIO** (Ubicaciones geográficas)
- **DIRECCION** (Direcciones físicas)
- **ORGANIZACION** (Organizaciones médicas)
- **ID_SUJETO_ASISTENCIA** (IDs de pacientes)
- **CORREO_ELECTRONICO** (Emails)
- **NUMERO_TELEFONO** (Teléfonos)
- **EDAD** (Edades)
- Y otros tipos específicos de PHI

### Propósito

- Entrenar modelos de NER para identificar PHI
- Evaluar sistemas de desidentificación
- Benchmark para comparar modelos
- Fine-tuning de modelos biomédicos (ej: bsc-bio-ehr-es)

---

## 📚 CARMEN-I Corpus

### ¿Qué es CARMEN-I?

**CARMEN-I** (Clinical Annotation and Retrieval for Medical Entities in Spanish) es un corpus de registros clínicos anotados para reconocimiento de entidades nombradas (NER) en español.

### Características Principales

| Característica | Detalle |
|----------------|---------|
| **Documentos** | ~2,000 registros clínicos |
| **Tipos de documentos** | Cartas de alta<br>Referencias<br>Informes de radiología |
| **Entidades PHI** | **5,895 entidades** anotadas |
| **Densidad** | ~2.9 entidades por documento |
| **Idioma** | Español (algunas secciones en catalán) |
| **Disponibilidad** | ✅ Público (PhysioNet) |
| **Fuente** | Nature Scientific Data |

### Diferencias con MEDDOCAN

- **Más documentos** (2,000 vs. 1,000)
- **Menos entidades por documento** (densidad menor)
- **Menos entidades totales** (5,895 vs. 22,795)
- **Diversidad de tipos de documentos** (cartas de alta, referencias, radiología)

---

## 📊 Comparación Directa

| Aspecto | MEDDOCAN | CARMEN-I |
|---------|----------|----------|
| **Documentos** | ~1,000 | ~2,000 |
| **Entidades PHI** | 22,795 | 5,895 |
| **Densidad (entidades/doc)** | ~22.8 | ~2.9 |
| **División Train/Dev/Test** | ✅ Sí (500/250/250) | ⚠️ No especificada |
| **Esquema de etiquetado** | IOB2 | IOB2 |
| **Calidad de anotación** | Alta (expertos) | Alta |
| **Diversidad de documentos** | Casos clínicos | Cartas de alta, referencias, radiología |
| **Idioma** | Español | Español (+ algunas secciones catalán) |
| **Uso principal** | Desidentificación específica | NER médico general (incluye PHI) |

---

## 🎯 ¿Cuándo Usar Cada Uno?

### Usa MEDDOCAN cuando:

✅ Necesitas **alta densidad de entidades** (más ejemplos por documento)
✅ Quieres un corpus **específicamente diseñado para desidentificación**
✅ Necesitas **división clara train/dev/test**
✅ Quieres comparar con otros modelos entrenados en MEDDOCAN
✅ Necesitas **más entidades totales** para entrenamiento

### Usa CARMEN-I cuando:

✅ Necesitas **más documentos** (2,000 vs. 1,000)
✅ Quieres **diversidad de tipos de documentos** (cartas de alta, referencias, radiología)
✅ Necesitas un corpus más grande para entrenamiento
✅ Quieres combinar con MEDDOCAN para más datos

---

## 🔄 Uso en tu Proyecto

### En tus Resultados de Evaluación:

**bsc-bio-ehr-es-meddocan:**
- Modelo evaluado en conjunto de test de MEDDOCAN
- Baseline sin fine-tuning: 76.05% Precision, 79.20% Recall

**bsc-bio-ehr-es-carmen-anon:**
- Modelo evaluado en conjunto de CARMEN-I (anonimizado)
- Baseline sin fine-tuning: 77.62% Precision, 77.20% Recall

**ner-meddocan-retrained:**
- Modelo fine-tuneado en MEDDOCAN
- Resultado: 94.93% Precision, 85.85% Recall

### ¿Por qué MEDDOCAN para Fine-tuning?

1. **Mayor densidad de entidades:** Más ejemplos por documento
2. **Específico para desidentificación:** Diseñado para PHI
3. **División clara:** Train/Dev/Test bien definidos
4. **Estándar de referencia:** Usado como benchmark en la comunidad

---

## 📈 Rendimiento Esperado

### Baselines (sin fine-tuning):

| Corpus | Precision | Recall | F1-Score |
|--------|----------|--------|----------|
| **MEDDOCAN** | ~76% | ~79% | ~77% |
| **CARMEN-I** | ~77% | ~77% | ~77% |

**Observación:** Ambos muestran rendimiento similar (~77% F1), confirmando que bsc-bio-ehr-es tiene capacidad inherente para identificar PHI.

### Con Fine-tuning:

| Corpus | Precision | Recall | F1-Score |
|--------|----------|--------|----------|
| **MEDDOCAN** | ~94% | ~86% | ~90% |

**Mejora:** Del ~77% → ~90% F1-Score (+13 puntos porcentuales)

---

## 🌍 Contexto Global

### Corpus Públicos de Desidentificación con PHI Labels:

| Idioma | Corpus | Documentos | PHI Entities |
|--------|--------|------------|--------------|
| **Inglés** | i2b2 2014 | 1,304 | 28,872 |
| **Inglés** | i2b2 2006 | 889 | ~16,000+ |
| **Español** | **MEDDOCAN** | ~1,000 | **22,795** |
| **Español** | **CARMEN-I** | 2,000 | **5,895** |

**Importante:** Solo **inglés y español** tienen corpus públicos de desidentificación con PHI labels. Todos los demás idiomas (francés, alemán, portugués, etc.) **NO tienen** corpus públicos disponibles.

---

## 💡 Implicaciones para tu Proyecto

### Por qué tu Pipeline Sintético es Valioso:

1. **Escasez de datos:** Solo 2 idiomas tienen corpus públicos
2. **Tamaño limitado:** MEDDOCAN tiene ~1,000 documentos, CARMEN-I tiene 2,000
3. **Tu pipeline:** Genera 14,035 documentos sintéticos (14x más que MEDDOCAN)
4. **Múltiples idiomas:** Puedes generar corpus para idiomas sin recursos

### Comparación:

| Fuente | Documentos | PHI Entities | Idioma |
|--------|------------|--------------|--------|
| **MEDDOCAN** | ~1,000 | 22,795 | Español |
| **CARMEN-I** | 2,000 | 5,895 | Español |
| **Tu Pipeline** | **14,035** | **~350,000+** | Español |

**Tu pipeline genera:**
- ✅ **14x más documentos** que MEDDOCAN
- ✅ **15x más documentos** que CARMEN-I
- ✅ Potencialmente para múltiples idiomas

---

## 📚 Referencias

- **MEDDOCAN:** Marimon et al. (2019) - meddocan.github.io
- **CARMEN-I:** Publicado en Nature Scientific Data - Disponible en PhysioNet
- **i2b2 2014:** Stubbs et al. (2015) - Benchmark en inglés

---

## 🎯 Conclusión

### MEDDOCAN:
- ✅ Corpus específico para desidentificación
- ✅ Alta densidad de entidades (22.8 por documento)
- ✅ Estándar de referencia en español
- ✅ Ideal para fine-tuning

### CARMEN-I:
- ✅ Más documentos (2,000)
- ✅ Diversidad de tipos de documentos
- ✅ Complementa a MEDDOCAN
- ✅ Útil para entrenamiento con más datos

### Ambos son:
- ✅ **Los únicos corpus públicos en español** con PHI labels
- ✅ **Críticos** para entrenar modelos de desidentificación
- ✅ **Referencias** para comparar rendimiento
- ✅ **Limitados en tamaño** (justificando tu pipeline sintético)

---

**En resumen:** MEDDOCAN y CARMEN-I son los dos únicos corpus públicos en español para entrenar modelos de desidentificación. MEDDOCAN tiene más entidades y está específicamente diseñado para desidentificación, mientras que CARMEN-I tiene más documentos y diversidad. Tu pipeline sintético genera significativamente más datos que ambos combinados.

