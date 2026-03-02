# Resumen de Actualización del Corpus

## Cambio Realizado

**Fecha:** $(Get-Date -Format "yyyy-MM-dd")

### Corpus Anterior
- **Ubicación:** `corpus_repo/corpus/documents`
- **Estado:** Respaldo guardado en `corpus_repo_old_backup`

### Nuevo Corpus
- **Ubicación:** `corpus_repo/corpus_v1/documents`
- **Fuente:** https://github.com/ramsestein/generate_corpus_anonimizacion/tree/main/corpus_v1
- **Documentos:** 14,035 archivos .txt
- **Entidades:** Archivos JSON en `corpus_repo/corpus_v1/entidades`

---

## Estructura del Nuevo Corpus

```
corpus_repo/
└── corpus_v1/
    ├── documents/          (14,035 archivos .txt)
    ├── entidades/          (archivos .json con anotaciones)
    ├── anonymized_documents/
    ├── doc_griegos/
    └── validation_results/
```

---

## Scripts Actualizados

### 1. `count_centro_salud_alamos.py`
- **Cambio:** Prioridad actualizada para usar `corpus_repo/corpus_v1/documents`
- **Ruta activa:** `corpus_repo/corpus_v1/documents` (primera en la lista)

### 2. `mostrar_corpus_paths.py`
- **Cambio:** Actualizado para mostrar `corpus_v1` como ruta principal
- **Rutas disponibles:** Incluye `corpus_v1` en la lista

---

## Verificación

✅ Nuevo corpus descargado y activo
✅ Corpus anterior respaldado como `corpus_repo_old_backup`
✅ Scripts actualizados para usar `corpus_v1`
✅ 14,035 documentos disponibles en `corpus_v1/documents`

---

## Próximos Pasos

Si necesitas actualizar otros scripts que usen el corpus:

1. Buscar referencias a `corpus_repo/corpus/documents`
2. Reemplazar con `corpus_repo/corpus_v1/documents`
3. Buscar referencias a `corpus_repo/corpus/entidades`
4. Reemplazar con `corpus_repo/corpus_v1/entidades`

---

## Notas

- El corpus anterior está respaldado y no se ha eliminado
- Los scripts ahora priorizan `corpus_v1` sobre otras rutas
- La estructura es compatible con los scripts existentes

