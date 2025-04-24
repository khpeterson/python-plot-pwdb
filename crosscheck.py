"""
Crosscheck the topologies specified in the various CoW *_model.txt
files with the geometries specified in the corresponding
pwdb_geo_*.csv files.  Optionally, rename the CoW dirs to match the
models.
"""

import pathlib
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('pwdbdir', help='pwdb root dir')
parser.add_argument(
    '-v', dest='verbose', help='show more debug', action='count', default=0
)
parser.add_argument(
    '--rename', dest='rename', help='rename dirs to match models',
    action='store_true'
)
args = parser.parse_args()

pwdb_path = pathlib.Path(args.pwdbdir)

topologies = ['Complete'] + sorted([
    'ACA_A1', 'PCoA_PCA_P1', 'PCoAs', 'ACoA', 'PCA_P1', 'PCoA'
])

model_names = {
    'Complete': 'Healty_model.txt',
    'ACA_A1': 'Missing_ACAA1_model.txt',
    'PCoA_PCA_P1': 'Missing_PCoAandPCAP1_model.txt',
    'PCoAs': 'Missing_PCoAs_model.txt',
    'ACoA': 'Missing_ACoA_model.txt',
    'PCA_P1': 'Missing_PCAP1_model.txt',
    'PCoA': 'Missing_PCoA_model.txt'
}

models = {}
geos = {}

for t in topologies:
    models[t] = pd.read_csv(
        pwdb_path.joinpath('pwdb_v2/Input Data/' + model_names[t]),
        delimiter='\t'
    )
    geos[t] = pd.read_csv(pwdb_path.joinpath(t + '/geo/pwdb_geo_0001.csv'))

mismatch = False
for k1 in topologies:
    for k2 in topologies:
        if (
            (len(models[k1]) == len(geos[k2])) and
            (models[k1]['Inlet node'] == geos[k2][' inlet_node']).min() and
            (models[k1]['Outlet node'] == geos[k2][' outlet_node']).min() and
            (models[k1]['Length [m]'] == geos[k2][' length']).min()
        ):
            print(f'models[{k1}] <== geos[{k2}]')
            if k1 != k2:
                mismatch = True
                if args.rename:
                    path = pwdb_path.joinpath(k2)
                    renamed_path = pwdb_path.joinpath(k2 + '_renamed_' + k1)
                    path.rename(renamed_path)

if mismatch:
    print("models and geometries don't match")
else:
    print("models and geometries match OK")

if args.rename:
    renamed_paths = pwdb_path.glob('*_renamed_*')
    for p in renamed_paths:
        k2 = p.name[0:p.name.index('_renamed_')]
        k1 = p.name[p.name.index('_renamed_') + 9:]
        trimmed_path = pwdb_path.joinpath(k1)
        print(f"renaming {p} as {trimmed_path}")
        p.rename(trimmed_path)
