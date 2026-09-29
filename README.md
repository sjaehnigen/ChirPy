# ChirPy

[*ChirPy*](https://github.com/sjaehnigen/chirpy) (_chiral python_) is a python package for chirality, dynamics, and molecular vibrations.


Main features:
- Computation of vibrational circular dichroism (VCD) from molecular dynamics (MD) and time-correlation functions (TCF)
- Application of the periodic gauge for magnetic moments and crystal symmetry in solid-state  
- Interpretation, processing, and creation of molecular topologies and supercells
- Analysis and visualisation of MD results 
    

Furthermore:
- Scientific visualisation
- Interfacing with VMD
- Processing of volumetric data and vector fields

(... work in progress)

## Package structure
*ChirPy* is organised into the following sub-packages under `src/chirpy/`:
- `classes` — core data structures (trajectories, molecular systems, quantum-chemical data, volumetric fields)
- `read` / `write` — parsers and writers for coordinate, volume, and mode file formats
- `create` — generation of supercells, collective variables, and input files
- `interface` — bridges to third-party software (CPMD, CP2K, Gaussian, Orca, VMD, PyMOL, Tinker, NAMD, Molden)
- `topology` — molecular topology, mapping, distribution, and dissection tools
- `physics` — electrodynamics, spectroscopy, statistical mechanics, and the modern theory of magnetisation
- `mathematics` — algebra and analysis helper routines
- `visualise` — plotting and scientific visualisation utilities

Command-line entry points wrapping these features are provided in `scripts/`.


## Installation 
Copy or clone the repository into a local directory. Open a bash terminal and change directory to the local copy of the repository.

Make sure you have the following packages installed:
- `python` >= 3.13
- `pip` >= 25.1
- `packmol` >= 20.0 (optional)

You can also use [Anaconda](https://anaconda.org) to create a *chirpy* environment from the delivered `conda_env.yml` file:
```shell
conda env create -f conda_env.yml
```

In the parent directory, run:
```shell
pip install .
```

*ChirPy* has now been installed and can be imported within a python environment:
```python
import chirpy as cp
```

Check that you installation is correct by running from a bash terminal the test suite in `tests/`:
```shell
python run_tests.py
```
or
```shell
./run_tests.py
```
(optional arguments: --verbose, --scripts)

Thank you for reporting bugs and issues to the [developers](https://github.com/sjaehnigen/chirpy/blob/master/AUTHORS.txt).

## Examples
Workable binaries can be found in the folder `scripts/` with some pre-implemented *ChirPy* features. Make sure you add this folder to PATH.

Available jupyter notebooks and data sets (produced with *ChirPy*, see [References](#references)):
- [Computation of Solid-State Vibrational Circular Dichroism in the Periodic Gauge](https://doi.org/10.5281/zenodo.4776907)
- [How Crystal Symmetry Dictates Non-Local Vibrational Circular Dichroism in the Solid State](https://doi.org/10.5281/zenodo.7228748)
- [The Genesis of OH-Stretching Vibrational Circular Dichroism in Chiral Molecular Crystals](https://doi.org/10.5281/zenodo.14222397)

(... under construction)

## References
Selected publications that used and/or developed *ChirPy*; see [sjaehnigen.github.io/publications.html](https://sjaehnigen.github.io/publications.html) for the full and up-to-date list.

1. [S. Jähnigen, A. Zehnacker, R. Vuilleumier; Computation of Solid-State Vibrational Circular Dichroism in the Periodic Gauge, *J. Phys. Chem. Lett.*, **2021**, *12* (30), 7213-7220.](https://doi.org/10.1021/acs.jpclett.1c01682) ([data](https://doi.org/10.5281/zenodo.4776907))
2. [S. Jähnigen, D. Sebastiani, R. Vuilleumier; The important role of non-covalent interactions
for the vibrational circular dichroism of lactic acid
in aqueous solution, *Phys. Chem. Chem. Phys.*, **2021**, *23*, 17232.](https://doi.org/10.1039/d1cp03106f)
3. [S. Jähnigen, K. Le Barbu-Debus, R. Guillot, R. Vuilleumier, A. Zehnacker; How Crystal Symmetry Dictates Non-Local Vibrational Circular Dichroism in the Solid State, *Angew. Chem. Int. Ed.*, **2023**, *62*, e202215599.](https://doi.org/10.1002/anie.202215599) ([data](https://doi.org/10.5281/zenodo.7228748))
4. [S. Jähnigen, R. Vuilleumier, A. Zehnacker; The genesis of OH-stretching vibrational circular dichroism in chiral molecular crystals, *Chemical Science*, **2025**, *16*, 9833-9842.](https://doi.org/10.1039/D4SC08055F) ([data](https://doi.org/10.5281/zenodo.14222397))

Note: some publications by the developers apply *ChirPy* to post-process or analyse trajectories from other software (e.g. CP2K, CPMD) without contributing new *ChirPy* features; e.g., the Girsanov-reweighting study (S. Jähnigen, B. G. Keller, *Commun. Appl. Math. Comput. Sci.*, **2026**, accepted) is such an application and is not itself a *ChirPy* development.

## Citing ChirPy
If you use *ChirPy* in your work, please cite it via its Zenodo record; see `CITATION.bib` for the corresponding BibTeX entry:

> S. Jähnigen; *ChirPy* -- A python package for chirality, dynamics, and molecular vibrations, **2022**. https://doi.org/10.5281/zenodo.4775330

## Contributing
Contributions, bug reports, and feature requests are welcome. Please open an issue or pull request on [GitHub](https://github.com/sjaehnigen/chirpy), or contact the [developers](https://github.com/sjaehnigen/chirpy/blob/master/AUTHORS.txt) directly.

## License
*ChirPy* is distributed under the [GNU General Public License v3.0 (or later)](https://github.com/sjaehnigen/chirpy/blob/master/LICENSE.txt).

