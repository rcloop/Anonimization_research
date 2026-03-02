#!/usr/bin/env python3
"""
Script para crear y configurar el entorno virtual para bias evaluation.
Funciona en Windows, Linux y Mac.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from pathlib import Path


def run_command(command, check=True):
    if isinstance(command, str):
        command = command.split()
    print(f"  Ejecutando: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: {e}")
        if e.stderr:
            print(f"  {e.stderr}")
        if check:
            sys.exit(1)
        return e


def get_venv_python(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def get_pip_command(venv_path: Path):
    if sys.platform == "win32":
        return [str(venv_path / "Scripts" / "pip.exe")]
    return [str(venv_path / "bin" / "pip")]


def main():
    parser = argparse.ArgumentParser(description="Bias Evaluation - Setup Virtual Environment")
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Instala requirements-minimal.txt (si existe).",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("Bias Evaluation - Setup Virtual Environment")
    print("=" * 80)
    print()

    script_dir = Path(__file__).parent.absolute()
    venv_path = script_dir / "venv"
    requirements_file = script_dir / ("requirements-minimal.txt" if args.minimal else "requirements.txt")

    print("[1/4] Verificando Python...")
    python_exe = sys.executable
    print(f"  Python: {python_exe}")
    version_result = run_command([python_exe, "--version"], check=False)
    if version_result.returncode != 0:
        print("ERROR: No se pudo verificar la versión de Python")
        sys.exit(1)
    print("✓ Python verificado")
    print()

    print(f"[2/4] Creando entorno virtual en: {venv_path}")
    if venv_path.exists():
        print("  El entorno virtual ya existe. Eliminando...")
        import shutil

        try:
            shutil.rmtree(venv_path)
            print("  ✓ Entorno virtual anterior eliminado")
        except Exception as e:
            print(f"  ERROR: No se pudo eliminar el entorno virtual: {e}")
            response = input("  ¿Continuar de todos modos? (s/n): ")
            if response.lower() != "s":
                sys.exit(1)

    venv.create(venv_path, with_pip=True)
    print("✓ Entorno virtual creado")
    print()

    print("[3/4] Actualizando pip...")
    pip_cmd = get_pip_command(venv_path)
    run_command(pip_cmd + ["install", "--upgrade", "pip"])
    print("✓ pip actualizado")
    print()

    print("[4/4] Instalando dependencias...")
    if not requirements_file.exists():
        print(f"ADVERTENCIA: No se encontró {requirements_file}")
        print("  Continuando sin instalar dependencias...")
    else:
        print(f"  Instalando desde: {requirements_file}")
        run_command(pip_cmd + ["install", "-r", str(requirements_file)])
        print("✓ Dependencias instaladas")
    print()

    print("[Verificación] Verificando instalación...")
    venv_python = get_venv_python(venv_path)
    try:
        import_check = subprocess.run(
            [str(venv_python), "-c", "import numpy; print('✓ numpy OK')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if import_check.returncode == 0:
            print(import_check.stdout.strip())
        else:
            print("  ADVERTENCIA: Algunas dependencias podrían no estar instaladas correctamente")
            if import_check.stderr:
                print(import_check.stderr.strip())
    except Exception as e:
        print(f"  ADVERTENCIA: No se pudo verificar las dependencias: {e}")
    print()

    print("=" * 80)
    print("Setup completado exitosamente!")
    print("=" * 80)
    print()
    print("Para activar el entorno virtual:")
    if sys.platform == "win32":
        print(f"  {venv_path}\\Scripts\\Activate.ps1")
    else:
        print(f"  source {venv_path}/bin/activate")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

