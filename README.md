## python-plot-pwdb: PWDB Plotting Scripts/Tools

These scripts/tools enable plotting with python of the virtual datasets
created by the Haemodynamic Modelling Research Group at King's College
London.  Specifically, the scripts will download, unpack and plot:

- [Dataset with Different Age Groups, PWDB v1 (2019)](http://haemod.uk/ageing)
- [Dataset with CoW Variations, PWDB v2 (2024)](http://haemod.uk/CoW)

### Installation

```
pip install -r requirements.txt
```

### Unpacking

To download and unpack the PWDB v1 (2019) and v2 (2024, CoW) datasets:
```bash
./unpack_pwdb.sh -d -1 pwdb-2019
./unpack_pwdb.sh -d pwdb-2024
```
Note: unpack_pwdb.sh depends on several command line tools and will
check for availability before running.

### Crosschecking

As of version 3 of the 2024 CoW dataset there is a discrepancy between
the geometries specified in the csv files of the various downloads and
the topologies specified by the v2 model.txt files.  To line them up:
```bash
python crosscheck.py --rename pwdb-2024
```

### Plotting

The plotting program, plot_pwdb.py, is a simple command line tool with
options to specify lists of signals, arterial sites, signal types, and
subjects.  One can also request to view all signals along the path
from the AorticRoot to a specific point in the arterial tree.
Subjects and signals are presented as a sequence of plots; arrow keys
on the keyboard navigate forward and backwards through the sequences.
Each plot in the sequence may be saved as a PDF for later viewing.

```
usage: plot_pwdb.py [-h] [-v]
                    [--signals SIGNALS] [--sites SITES]
                    [--types TYPES] [--subjects SUBJECTS]
                    [--path PATH] [--model MODEL] [--query]
                    [--dir DIR] [--batch]
                    pwdbdirs [pwdbdirs ...]

positional arguments:
  pwdbdirs             pwdb root dir(s)

options:
  -h, --help           show this help message and exit
  -v                   show more debug
  --signals SIGNALS    specify signals to plot (e.g. "Radial_U,Brachial_U", default: all)
  --sites SITES        specify sites to plot (e.g. "LEIA,RICA")
  --types TYPES        specify signal types to plot (default: "PPG,P,A,Q,U")
  --subjects SUBJECTS  specify subjects to plot, (e.g., 0,2-4,7,10-12)
  --path PATH          plot signals in path to prefix specified by PATH(e.g. "Digital", requires MODEL)
  --model MODEL        use model MODEL to determine path to signal specified by PATH
  --query              print sites[signals] in path to PATH and stop
  --dir DIR            dir for saving figures
  --batch              disable plot show
```


### Examples

To compare the flow rate of v1 to v2/Complete at the Radial artery for baseline subjects aged 25, 55 and 75 (top left of Figure 4 of [Machine learning-based pulse wave analysis for classification of circle of Willis topology: An in silico study with 30,618 virtual subjects](https://www.sciencedirect.com/science/article/pii/S1746809424010577?via%3Dihub)):
```bash
python plot_pwdb.py --subjects 1,4,6 --signals Radial_U pwdb-2019 pwdb-2024/Complete
```

To compare the flow rate at the LeftMiddleCerebralArtery(M1) site across all CoW topologies for the 25-year-old baseline subject ([top left of Figure 6 before time stretching](https://www.sciencedirect.com/science/article/pii/S1746809424010577?via%3Dihub)):
```bash
python plot_pwdb.py --subjects 1 --sites 'LeftMiddleCerebralArtery(M1)' --types U \
    pwdb-2024/{Complete,ACoA,PCoA,PCoAs,ACA_A1,PCA_P1,PCoA_PCA_P1}
```

To view all available flow, pressure and area signals along the path
from AorticRoot to Digital for the 25-year-old baseline subject :
```bash
python plot_pwdb.py --subjects 1 --path Digital --types U,P,A \
    --model pwdb-2024/pwdb_v2/Input\ Data/Healty_model.txt pwdb-2024/Complete
```

To plot and generate PDF files of the same path but for all CoW topologies:
```bash
python plot_pwdb.py --dir pdf_subject1 --subjects 1 --path Digital --types U,P,A \
    --model pwdb-2024/pwdb_v2/Input\ Data/Healty_model.txt \
    pwdb-2024/{Complete,ACoA,PCoA,PCoAs,ACA_A1,PCA_P1,PCoA_PCA_P1}
```

To generate PDF files for all subjects in batch mode (without plotting):
```bash
python plot_pwdb.py --dir pdf_all --batch --path Digital --types U,P,A \
    --model pwdb-2024/pwdb_v2/Input\ Data/Healty_model.txt \
    pwdb-2024/{Complete,ACoA,PCoA,PCoAs,ACA_A1,PCA_P1,PCoA_PCA_P1}
```
