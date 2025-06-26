import glob
from pathlib import Path
import nbformat
from nbconvert import PythonExporter
import re
import os

print(os.getcwd())

# get all notebooks from the docs
nb_files = glob.glob('book/*.ipynb')
nb_files = [Path(x) for x in nb_files]
pattern = re.compile(r"\d+.*")
nb_files = [f for f in nb_files if pattern.match(f.name)]

print(f"Found {len(nb_files)} notebooks to process.")

for f in nb_files:
    print(f"Processing {f.name}")
    # Create function name by cleaning filename
    base_name = re.sub(r'^\d+', '', f.stem).replace('-', '_')
    py_filename = f.with_suffix('.py').name.replace('-', '_')
    py_path = Path('src/napari_imagegrains/_tests').joinpath(f'test_{py_filename}')

    # Load the notebook
    with open(f, "r", encoding="utf-8") as nb_fp:
        notebook = nbformat.read(nb_fp, as_version=4)

    # Convert to Python script
    exporter = PythonExporter()
    source_code, _ = exporter.from_notebook_node(notebook)

    # Replace viewer assignment
    source_code = re.sub(r'viewer\s*=\s*napari\.Viewer\(\s*\)', 'viewer = make_napari_viewer()', source_code)

    # Comment out get_ipython() lines
    source_code = re.sub(r'^(.*get_ipython\(\).*)', r'# \1', source_code, flags=re.MULTILINE)

    # Indent all lines (skip blank lines)
    indented_lines = ['    ' + line if line.strip() else line for line in source_code.splitlines(keepends=True)]

    # Compose final script content
    function_def = f'def {py_path.stem}(make_napari_viewer):\n'
    function_call = f'\n\nif __name__ == "__main__":\n    {base_name}(make_napari_viewer)\n'

    final_code = ['import pytest\n\n', function_def] + indented_lines + [function_call]

    # Save to .py file
    with open(py_path, "w", encoding="utf-8") as fp:
        fp.writelines(final_code)