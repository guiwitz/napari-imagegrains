# napari-imagegrains

[![License BSD-3](https://img.shields.io/pypi/l/napari-imagegrains.svg?color=green)](https://github.com/guiwitz/napari-imagegrains/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-imagegrains.svg?color=green)](https://pypi.org/project/napari-imagegrains)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-imagegrains.svg?color=green)](https://python.org)
[![tests](https://github.com/guiwitz/napari-imagegrains/workflows/tests/badge.svg)](https://github.com/guiwitz/napari-imagegrains/actions)
[![codecov](https://codecov.io/gh/guiwitz/napari-imagegrains/branch/main/graph/badge.svg)](https://codecov.io/gh/guiwitz/napari-imagegrains)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-imagegrains)](https://napari-hub.org/plugins/napari-imagegrains)

An interactive napari plugin for the [ImageGrains](https://github.com/dmair1989/imagegrains) software.

----------------------------------

## Installation

We recommend to install the plugin in an isolated environment as provided by conda. For conda create an appropriate environment with (do not use Python more recent than 3.11):

    conda create -n napari-imagegrains -c conda-forge python=3.11 napari pyqt
    conda activate napari-imagegrains
    pip install napari-imagegrains


To install latest development version :

    pip install git+https://github.com/guiwitz/napari-imagegrains.git

Or if you want to contribute to the plugin, fork the repository, clone it locally and install it in editable mode:

    pip install -e .


## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-imagegrains" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

## Authors

The original software ImageGrain was developed by David Mair, Institute of Geological Sciences, University of Bern. The current plugin, a user-interface for the ImageGrains software, was developed by Guillaume Witz and Michael Horn, Data Science Lab, University of Bern in collaboration with David Mair.

## Citation

If you use this software, please cite the following publication: Mair, D., Witz, G., Do Prado, A.H., Garefalakis, P. & Schlunegger, F. (2023) Automated detecting, segmenting and measuring of grains in images of fluvial sediments: The potential for large and precise data from specialist deep learning models and transfer learning. Earth Surface Processes and Landforms, 1–18. <https://doi.org/10.1002/esp.5755>.


[napari]: https://github.com/napari/napari
[copier]: https://copier.readthedocs.io/en/stable/
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[napari-plugin-template]: https://github.com/napari/napari-plugin-template

[file an issue]: https://github.com/guiwitz/napari-imagegrains/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
