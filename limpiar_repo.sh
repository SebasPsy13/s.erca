#!/bin/bash
# ================================================================
# limpiar_repo.sh — Limpieza completa del repositorio sistema-erca
# Ejecutar desde la raíz del repositorio clonado localmente.
# ================================================================

set -e

echo "🧹 Limpiando archivos y carpetas innecesarias..."

# --- Carpetas de versiones antiguas ---
git rm -r --cached --ignore-unmatch streamlit-erca/
git rm -r --cached --ignore-unmatch github-ready/
rm -rf streamlit-erca/
rm -rf github-ready/

# --- Documentación redundante (queda solo README.md) ---
git rm --cached --ignore-unmatch DEPLOYMENT_RENDER.md
git rm --cached --ignore-unmatch GUIA_IMPLEMENTACION.md
git rm --cached --ignore-unmatch INICIO_RAPIDO.md
git rm --cached --ignore-unmatch INSTRUCCIONES_API.md
git rm --cached --ignore-unmatch RESUMEN_ENTREGABLES.md
rm -f DEPLOYMENT_RENDER.md GUIA_IMPLEMENTACION.md INICIO_RAPIDO.md INSTRUCCIONES_API.md RESUMEN_ENTREGABLES.md

# --- Datos de pacientes (no deben estar en un repo público) ---
git rm --cached --ignore-unmatch pacientes.csv
git rm --cached --ignore-unmatch pacientes.xlsx
git rm --cached --ignore-unmatch pacientes_maestro_TOTAL.xlsx
rm -f pacientes.csv pacientes.xlsx pacientes_maestro_TOTAL.xlsx

# --- Base de datos SQLite (no deben subirse) ---
git rm --cached --ignore-unmatch sistema_erca.db
rm -f sistema_erca.db

# --- Artefactos de sistema operativo ---
git rm --cached --ignore-unmatch .localized
rm -f .localized

# --- runtime.txt (para Heroku/Render, no Railway) ---
git rm --cached --ignore-unmatch runtime.txt
rm -f runtime.txt

echo ""
echo "✅ Limpieza completada."
echo ""
echo "Ahora copia los archivos corregidos a este directorio:"
echo "  main.py, index.html, requirements.txt, Procfile, .gitignore"
echo ""
echo "Luego haz commit y push:"
echo "  git add ."
echo "  git commit -m 'fix: correcciones Railway, Postgres, seguridad y limpieza'"
echo "  git push origin main"
