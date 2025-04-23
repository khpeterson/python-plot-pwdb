"""
Plot records of PWDB by signals, sites, types and along an aterial
path for each of the specified directories (typically one dir per CoW
topology).  Plots can be saved as PDFs and runs can be batched.
"""

import argparse
import pathlib
import pprint
import sys

from collections import OrderedDict
from itertools import pairwise

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import wfdb

from subplotseq import SubplotSequence


# command line argument handling

def signal_list(arg_value):
    """Parse a list of signals with comma-separated values."""

    sig_names = []
    arg_value_parts = map(str.strip, arg_value.split(','))

    for part in arg_value_parts:
        # check for mapping from signal prefix to site and expected type
        try:
            part_split = part.split('_')
            part_prefix = part_split[0]
            part_suffix = part_split[1]
            _ = get_site_name(part_prefix)
            _ = default_sig_types.index(part_suffix)
            sig_names.append(part)
        except (KeyError, IndexError, ValueError) as e:
            raise argparse.ArgumentTypeError(f"Unrecognized signal name '{part}'") from e

    # remove duplicates
    return list(dict.fromkeys(sig_names))


def site_list(arg_value):
    """Parse a list of sites with comma-separated values."""

    sig_sites = []
    arg_value_parts = map(str.strip, arg_value.split(','))

    for part in arg_value_parts:
        # check for mapping from signal prefix to site
        try:
            _ = get_signal_prefix(part)
            sig_sites.append(part)
        except KeyError as e:
            raise argparse.ArgumentTypeError(f"Unrecognized site '{part}'") from e

    # remove duplicates
    return list(dict.fromkeys(sig_sites))


def signal_prefix(arg_value):
    """Parse a signal prefix."""

    # check for mapping from signal prefix to site
    try:
        _ = get_site_name(arg_value)
    except KeyError as e:
        raise argparse.ArgumentTypeError(f"Unrecognized signal prefix '{arg_value}'") from e

    return arg_value


def signal_type_list(arg_value):
    """Parse a list of signal types with comma-separated values."""

    sig_types = []
    arg_value_parts = map(str.strip, arg_value.split(','))

    for part in arg_value_parts:
        if part in default_sig_types:
            sig_types.append(part)
        else:
            raise argparse.ArgumentTypeError(
                f"Unrecognized signal type '{part}', expected one of {default_sig_types}"
            )

    # remove duplicates
    return list(dict.fromkeys(sig_types))


def subject_list(arg_value):
    """Parse a list of subjects with comma-separated values and ranges."""

    subject_indices = []
    subject_parts = arg_value.split(',')

    for part in subject_parts:
        if '-' in part:
            # Handle range format (e.g., "1-5")
            try:
                start, end = map(int, part.split('-'))
                subject_indices.extend(range(start, end + 1))
            except ValueError as e:
                raise argparse.ArgumentTypeError(
                    f"Invalid range format '{part}'. Expected format: 'start-end'"
                ) from e
        else:
            # Handle single number
            try:
                subject_indices.append(int(part))
            except ValueError as e:
                raise argparse.ArgumentTypeError(
                    f"Invalid subject index '{part}'. Expected an integer."
                ) from e

    # Remove duplicates and sort
    return sorted(set(subject_indices))


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument('pwdbdirs', nargs='+', help='pwdb root dir(s)')
    parser.add_argument('-v', dest='verbose', action='count', default=0,
                        help='show more debug')

    parser.add_argument('--signals', dest='signals', type=signal_list,
                        help='specify signals to plot (e.g. "Radial_U,Brachial_U", default: all)')
    parser.add_argument('--sites', dest='sites', type=site_list,
                        help='specify sites to plot (e.g. "LEIA,RICA")')
    parser.add_argument('--types', dest='types', type=signal_type_list,
                        help='specify signal types to plot (default: "PPG,P,A,Q,U")')
    parser.add_argument('--subjects', dest='subjects', type=subject_list,
                        help='specify subjects to plot, (e.g., 0,2-4,7,10-12)')

    parser.add_argument('--path', dest='path', type=signal_prefix,
                        help='plot signals in path to prefix specified by PATH'
                        '(e.g. "Digital", requires MODEL)')
    parser.add_argument('--model', dest='model',
                        help='use model MODEL to determine path to signal specified by PATH')
    parser.add_argument('--query', dest='query', action='store_true',
                        help='print sites[signals] in path to PATH and stop')

    parser.add_argument('--dir', dest='dir', type=str, default=None,
                        help='dir for saving figures')
    parser.add_argument('--batch', dest='batch', action='store_true',
                        help="disable plot show")

    return parser.parse_args()


# map model site names to wfdb signal names
# copied from pwdb_v2/export_pwdb.m
site_signal_prefix_mapping_v2 = {
    'Ascending Aorta': 'AorticRoot',
    'DTA 1': 'ThorAorta',
    'Abdominal Aorta 4': 'AbdAorta',
    'Abdominal Aorta 5': 'IliacBif',
    'Left Common Carotid Artery': 'LCCA',
    'Left Superior Temporal Artery': 'SupTemporal',
    'Left Brachial Artery': 'Brachial',
    'Left Radial Artery': 'Radial',
    'Left Digital Artery 3': 'Digital',
    'LEIA': 'CommonIliac',
    'Left Femoral Artery': 'Femoral',
    'Left Anterior Tibial Artery': 'AntTibial',
    'RICA': 'ICA',
    'MiddleCerebralArtery(M1)': 'MCA',  # special handling for Complete
    'LeftMiddleCerebralArtery(M1)': 'LMCA',
    'RightMiddleCerebralArtery(M1)': 'RMCA',
    'Right Posterior Cerebral Artery 2': 'PCA',
    'RightAnteriorCerebralArtery2': 'ACA',
    'Left Vertebral Artery': 'LVA',
    'Basilar Artery 2': 'BA',
    'Right Vertebral Artery': 'RVA',
    'Right Common Carotid Artery': 'RCCA'
}

signal_prefix_site_mapping_v2 = {v: k for k, v in site_signal_prefix_mapping_v2.items()}

# v1 (2019) mapping copied from:
# https://github.com/peterhcharlton/pwdb/blob/master/pwdb_v0.1/export_pwdb.m
# https://github.com/peterhcharlton/pwdb/blob/master/pwdb_v0.1/Input%20Data/116_artery_model.txt
site_signal_prefix_mapping_v1 = {
    'Ascending Aorta': 'AorticRoot',
    'Descending Thoracic Aorta I': 'ThorAorta',
    'Abdominal Aorta IV': 'AbdAorta',
    'Abdominal Aorta V': 'IliacBif',
    'Left Common Carotid Artery': 'Carotid',
    'Left Superior Temporal Artery': 'SupTemporal',
    'Left Superior Middle Cerebral Artery (M2)': 'SupMidCerebral',
    'Left Brachial Artery': 'Brachial',
    'Left Radial Artery': 'Radial',
    'Left Digital Artery III': 'Digital',
    'Left External Iliac Artery': 'CommonIliac',
    'Left Femoral Artery': 'Femoral',
    'Left Anterior Tibial Artery': 'AntTibial'
}

signal_prefix_site_mapping_v1 = {v: k for k, v in site_signal_prefix_mapping_v1.items()}


def get_site_name(prefix):
    """Get site name from signal prefix, handle fallback to v1"""
    try:
        site_name = signal_prefix_site_mapping_v2[prefix]
    except KeyError:
        site_name = signal_prefix_site_mapping_v1[prefix]
    return site_name


def get_signal_prefix(site_name):
    """Get signal_prefix from site name, handle fallback to v1"""
    try:
        prefix = site_signal_prefix_mapping_v2[site_name]
    except KeyError:
        prefix = site_signal_prefix_mapping_v1[site_name]
    return prefix


def get_inlet_name_and_node(model_df, prefix):
    """Get inlet node and site name from model dataframe corresponding to signal_prefix"""
    try:
        inlet_name = signal_prefix_site_mapping_v2[prefix]
        inlet_node = model_df[model_df['Name'] == inlet_name]['Inlet node'].values[0]
        inlet_mapping = site_signal_prefix_mapping_v2
    except (KeyError, IndexError):
        inlet_name = signal_prefix_site_mapping_v1[prefix]
        inlet_node = model_df[model_df['Name'] == inlet_name]['Inlet node'].values[0]
        inlet_mapping = site_signal_prefix_mapping_v1
    return inlet_name, inlet_node, inlet_mapping


def get_signal_onset_times(sig_name, subject_onset_times):
    """
    Need special handling because Complete combines RMCA and LMCA as MCA
    """
    signal_onset_times = []
    for ot in subject_onset_times:
        key = ' ' + sig_name
        try:
            value = ot[key]
        except KeyError as e:
            # Complete combines RMCA and LMCA as MCA
            if sig_name.startswith('RMCA_') or sig_name.startswith('LMCA_'):
                key = ' ' + 'MCA_' + sig_name[5:]
                value = ot[key]
            else:
                raise e
        signal_onset_times.append(value)
    return signal_onset_times


def get_signal_idx(sig_name, record):
    """
    Need special handling because Complete combines RMCA and LMCA as MCA
    """
    try:
        sig_idx = record.sig_name.index(sig_name + ',')
    except ValueError as e:
        # Complete combines RMCA and LMCA as MCA
        if sig_name.startswith('RMCA_') or sig_name.startswith('LMCA_'):
            sig_idx = record.sig_name.index(f'MCA_{sig_name[5:]},')
        else:
            raise e
    return sig_idx


def find_non_common_elements(lists):
    """Finds elements that are not common across all lists"""
    all_elements = set()
    common_elements = set()
    for e in lists:
        s = set(e)
        common_elements.update(all_elements.intersection(s))
        all_elements.update(s)
    return all_elements.difference(common_elements)


def get_all_sig_names(record0_paths):
    """Check for consistency and consolidate signal names across all records"""
    record0_names = [p.with_suffix('') for p in record0_paths]
    record0s = [wfdb.rdrecord(n, smooth_frames=False) for n in record0_names]
    # skip trailing comma
    record0_sig_names = [[s[:-1] for s in r.sig_name] for r in record0s]
    if len(record0_sig_names) == 1:
        # only one pwdbdir given, include all signal names
        sig_names = record0_sig_names[0]
    else:
        # check for signal names not commont to all records
        non_common_names = find_non_common_elements(record0_sig_names)
        if len(non_common_names) == 0:
            # everythings is common, return first/any list of names
            sig_names = record0_sig_names[0]
        else:
            # only acceptable non-overlapping signal names start with MCA/LMCA/RMCA
            # need to check pairwise to be sure this is always the case
            for a, b in pairwise(record0_sig_names):
                nc = find_non_common_elements([a, b])
                if len(nc) == 0:
                    continue
                # FIXME: to be really strict should be checking for
                # matching signal types too.  For now just make sure non-common
                # includes only MCA+LMCA+RMCA and nothing else
                is_mca = False
                is_lmca = False
                is_rmca = False
                not_mca = False
                for n in nc:
                    is_mca = is_mca or n.startswith('MCA')
                    is_lmca = is_lmca or n.startswith('LMCA')
                    is_rmca = is_rmca or n.startswith('RMCA')
                    not_mca = not_mca or not (is_mca or is_lmca or is_rmca)
                if not is_mca or not is_lmca or not is_rmca or not_mca:
                    raise RuntimeError('All signal names are not consistent across'
                                       'pwdbdirs, specify some specific signals intead.')
            # pairwise check is good, return list of names with LMCA/RMCA
            # special handling above will map to MCA as needed plotting overlay
            lmca_rmca_sig_names = [s for s in record0_sig_names
                                   if (any(n.startswith('LMCA') for n in s) and
                                       any(n.startswith('RMCA') for n in s))]
            sig_names = lmca_rmca_sig_names[0]
    return sig_names


default_sig_types = ['P', 'U', 'A', 'PPG']

units = {
    'PPG': 'au',
    'P': 'mmHg',
    'A': 'm2',
    'Q': 'm3/sec',
    'U': 'm/sec'
}


def trace_path(model_df, prefix):
    """
    Trace path from Inlet node to site specified by signal_prefix and return ordered
    dictionary of site/signal names.
    """
    path = OrderedDict()
    inlet_name, inlet_node, inlet_mapping = get_inlet_name_and_node(model_df, prefix)
    path[inlet_name] = inlet_mapping.get(inlet_name)
    while inlet_node != 1:
        inlet_df = model_df[model_df['Outlet node'] == inlet_node]
        inlet_name = inlet_df['Name'].values[0]
        path[inlet_name] = inlet_mapping.get(inlet_name)
        inlet_node = inlet_df['Inlet node'].values[0]
    return OrderedDict(reversed(list(path.items())))


def flatten(xss):
    """Flatten nested list"""
    return [x for xs in xss for x in xs]


def trim_signal(sig_len, sig_v, verbose=0):
    """Trim trailing NaNs and zeros"""
    if np.max(np.isnan(sig_v)):
        # sometimes a trailing nan
        first_nan_index = np.argmax(np.isnan(sig_v))
        trailing_nan_count = sig_len - first_nan_index
        if verbose > 0:
            print(f'*** detected nan at index {first_nan_index}, '
                  f'sig_len = {sig_len}, trimming by {trailing_nan_count}')
        assert 0 < trailing_nan_count <= 16
        sig_len -= trailing_nan_count
        sig_v = sig_v[:-trailing_nan_count]

    if np.argmax(sig_v[::-1] != 0):
        # sometimes trailing zeros
        first_zero_index = sig_len - np.argmax(sig_v[::-1] != 0)
        trailing_zero_count = sig_len - first_zero_index
        if verbose > 0:
            print(f'*** detected 0 at index {first_zero_index}, '
                  f'sig_len = {sig_len}, trimming by {trailing_zero_count}')
        assert 0 < trailing_zero_count <= 100
        sig_len -= trailing_zero_count
        sig_v = sig_v[:-trailing_zero_count]

    return sig_len, sig_v


def main():
    """Run"""
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    # pylint: disable=unnecessary-comprehension

    args = parse_arguments()

    if args.path and not args.model:
        raise RuntimeError(f'A model is required to determine the path to {args.path}.')

    # set up for saving figures in sequence
    if args.dir:
        savefig_dir = args.dir
        pathlib.Path(savefig_dir).mkdir(parents=True, exist_ok=True)
        # if already figures in savefig_dir then append to sequence
        figure_files = list(pathlib.Path(savefig_dir).glob('**/Figure_*.pdf'))
        savefig_num = len(figure_files) + 1
    else:
        savefig_dir = None
        savefig_num = 0

    def savefig(ax):
        """Save axes to PDF in sequence"""
        nonlocal savefig_num
        if savefig_dir:
            ax.set_visible(True)
            plt.sca(ax)
            plt.savefig(f'{savefig_dir}/Figure_{savefig_num:04d}.pdf')
            ax.set_visible(False)
            savefig_num += 1

    # collect paths.  for explicit ordering specify all paths, e.g.
    # pwdb-2024/{Complete,ACoA,PCoA,PCoAs,ACA_A1,PCA_P1,PCoA_PCA_P1}
    # otherwise signals will be overlaid in alphabetical order
    base_paths = [pathlib.Path(d) for d in args.pwdbdirs]
    glob_paths = [[p for p in sorted(b.glob('**/PWs/wfdb'))] for b in base_paths]
    wfdb_paths = flatten(glob_paths)

    # all records by subject for each path in args.pwdbdirs, starting with Complete
    all_record_paths = [sorted(p.glob('pwdb*.dat')) for p in wfdb_paths]

    if len(all_record_paths) == 0 or len(all_record_paths[0]) == 0:
        raise RuntimeError('No wfdb records found.')

    # all onset times by subject for each path in args.pwdbdirs, starting with Complete
    all_onset_times = [
        pd.read_csv(p.parent.parent.joinpath('pwdb_onset_times.csv')) for p in wfdb_paths
    ]

    if args.types:
        sig_types = args.types
    else:
        sig_types = default_sig_types

    if args.signals:
        sig_names = args.signals

    elif args.path:
        # expecting path to be available as a signal prefix
        model_df = pd.read_csv(args.model, delimiter='\t')
        path = trace_path(model_df, args.path)
        print('tracing path:')
        pprint.pp(path)
        sig_names = flatten([[f'{v}_{s}' for s in sig_types]
                            for k, v in path.items() if v is not None])
    elif args.sites:
        sig_sites = args.sites
        sig_prefixes = [get_signal_prefix(s) for s in sig_sites]
        sig_names = flatten([[f'{p}_{s}' for s in sig_types]
                             for p in sig_prefixes])
    else:
        # all available signal names, consolidated
        sig_names = get_all_sig_names([p[0] for p in all_record_paths])

    if args.verbose > 0:
        print(f'sig_names = {sig_names}')

    if args.query:
        sys.exit(0)

    # plot in sequence, use arrow keys to go forward/backward
    pltseq = SubplotSequence(figsize=(16, 8))

    # iterate through subjects with slices across paths in args.pwdbdirs
    # (typically CoW variations, starting with Complete)
    for i, paths in enumerate(zip(*all_record_paths)):
        # Skip subjects not in the specified list
        if args.subjects and (i+1) not in args.subjects:
            continue

        records = [wfdb.rdrecord(p.with_suffix(''), smooth_frames=False) for p in paths]

        # Extract onset times for this subject
        subject_onset_times = [ot.iloc[i] for ot in all_onset_times]

        # now iterate through sig_names in seqeuence, one plot per signal
        for sig_name in sig_names:
            if args.verbose > 0:
                print(f'plotting {sig_name}')

            sig_name_split = sig_name.split('_')
            sig_name_prefix = sig_name_split[0]
            sig_name_suffix = sig_name_split[1]
            site_name = get_site_name(sig_name_prefix)

            # Extract onset times for this signal across all paths
            signal_onset_times = get_signal_onset_times(sig_name, subject_onset_times)

            axs = pltseq.figure.subplots(1, 1, sharex=True)
            axs.set_title(f'{records[0].record_name}: {sig_name} ({site_name})', fontsize=12)

            # now iterate through slice across paths in args.pwdbdirs
            for path, record, onset_time in zip(paths, records, signal_onset_times):
                record_name = path.with_suffix('')
                if args.verbose > 0:
                    print(f'plotting {record_name}')

                sig_idx = get_signal_idx(sig_name, record)
                sig_v = record.e_p_signal[sig_idx]
                dt = 1.0 / record.fs
                sig_len = record.sig_len

                # trim trailing NaNs and zeros
                sig_len, sig_v = trim_signal(sig_len, sig_v, args.verbose)

                # map onset times into [0, cardiac_cycle_duration)
                cardiac_cycle_duration = record.sig_len * dt
                if onset_time >= cardiac_cycle_duration:
                    if args.verbose > 0:
                        print(f'*** wrapping onset_time = {onset_time}, '
                              f'cardiac_cycle_duration = {cardiac_cycle_duration}')
                    onset_time -= cardiac_cycle_duration

                if args.verbose > 2:
                    print(f'{record_name}: onset_time[{sig_name}] = {onset_time}')

                sig_t = onset_time + np.arange(0, sig_len) * dt

                # always start plots at t=0, roll to accomodate
                if onset_time > 0:
                    wrap_select = sig_t >= sig_len * dt
                    sig_t = np.concatenate((sig_t[wrap_select] - sig_len * dt,
                                            sig_t[~wrap_select]))
                    sig_v = np.concatenate((sig_v[wrap_select], sig_v[~wrap_select]))

                axs.plot(sig_t, sig_v, label=path.parts[-4])

            axs.set_xlabel('Time (s)')
            axs.set_ylabel(units[sig_name_suffix])
            axs.grid(True)
            axs.legend()
            pltseq.add(axs)
            savefig(axs)

    if not args.batch:
        pltseq.show()


if __name__ == "__main__":
    main()
