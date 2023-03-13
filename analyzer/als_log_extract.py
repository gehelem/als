from argparse import ArgumentParser

import csv
import re
import sys
from pathlib import Path

SECTION = "=" * 50
SUB_SECTION = "-" * 50

_timing_candidates = list()

preprocess_timing_functions = [
    'read_disk_image()',
    "RemoveDark.process_image()",
    'HotPixelRemover.process_image()',
    "Debayer.process_image()",
    "Standardize.process_image()"
]

stacking_timing_functions = [

    'Stacker._find_transformation()',
    'Stacker._align_image()',
    'Stacker._stack_image()'
]

post_process_timing_functions = [

    "AutoStretch.process_image()",
    "Levels.process_image()",
    "ColorBalance.process_image()",
    "ImageSaver._save_image()"
]

timing_families = {
    "pre_processing": preprocess_timing_functions,
    "stacking": stacking_timing_functions,
    "post_process": post_process_timing_functions
}


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "-i",
        "--in_log",
        help="path to the als.log file",
        default=Path.home().joinpath(Path("als.log")))

    arg_parser.add_argument(
        "-o",
        "--out_folder",
        help="path to the folder where CSV files are written",
        default="./csv")

    args = arg_parser.parse_args()

    log_file = args.in_log
    csv_out_folder = args.out_folder
    Path(csv_out_folder).mkdir(parents=True, exist_ok=True)

    print(f"Parsing ALS log file {log_file}...")
    with open(log_file) as logfile:
        lines = logfile.readlines()

    # reassemble multiline entries
    buffer: str = "START"
    entries = list()
    for line in lines:
        line = line.replace("\n", "")
        if re.search("^\\d{4}", line):
            entries.append(buffer)
            buffer = line
        else:
            buffer += line
    entries.append(buffer)
    print(f'Reassembled {len(entries)} log entries')

    print(SECTION)
    print("Exporting functions timings...")
    print(SUB_SECTION)
    function_returns = list(filter(lambda l: "returned" in l, entries))
    print(f"Collected {len(function_returns)} function timings")
    function_timings_dict = extract_function_timings(function_returns)
    thread_timings_dict = extract_thread_timings(function_returns)
    write_timings_csv_files(function_timings_dict, csv_out_folder)

    print(SECTION)
    print("Exporting alignment data...")
    print(SUB_SECTION)
    write_stack_data_csv(entries, csv_out_folder)

    print(SECTION)
    print("Exporting every function return...")
    print(SUB_SECTION)
    returns = {
        'timestamp': list(),
        'thread': list(),
        'module': list(),
        'name': list(),
        'ret_value': list(),
        'elapsed': list(),
    }

    for ret in function_returns:
        tokens = tokenize(ret)
        returns['timestamp'].append(" ".join(tokens[:2]))
        returns['thread'].append(tokens[2])
        returns['module'].append(tokens[3])
        returns['name'].append(tokens[5])
        returns['ret_value'].append(tokens[7:-3])
        returns['elapsed'].append(tokens[-2])
    write_csv("global_returns", csv_out_folder, returns)

    print(SECTION)
    print("Threads total times (in s):")
    print(SUB_SECTION)
    for thread, total in thread_timings_dict.items():
        print(f"{thread:<11}: {(total / 1000):>8.2f} s")


def write_stack_data_csv(entries, out_folder):
    stacker_logs = list(filter(lambda l: re.search("\\sals\\.stack\\s", l), entries))
    stacking_data = {
        'rotation': [],
        'x_trans': [],
        'y_trans': [],
        'scale': [],
        'matches': [],
        'req_matches': [],
        'ratio': [],
        'accepted': []
    }
    for i in range(len(stacker_logs)):
        line = stacker_logs[i]
        if re.search("als.stack.*Stacker._find_transformation.*returned", line):
            ratio_line = stacker_logs[i - 6]
            rotation_line = stacker_logs[i - 5]
            translation_line = stacker_logs[i - 4]
            scale_line = stacker_logs[i - 3]
            matches_line = stacker_logs[i - 2]

            ratio_tokens = tokenize(ratio_line)
            rotation_tokens = tokenize(rotation_line)
            scale_toknes = tokenize(scale_line)
            matches_tokens = tokenize(matches_line)

            stacking_data['ratio'].append(float(ratio_tokens[-1]))
            stacking_data['rotation'].append(float(rotation_tokens[-1]))
            trans_matcher = re.search("\[\s*(\S+)\s+(\S+)\s*\]", translation_line)
            stacking_data['x_trans'].append(float(trans_matcher.group(1)))
            stacking_data['y_trans'].append(float(trans_matcher.group(2)))
            stacking_data['scale'].append(float(scale_toknes[-1]))
            stacking_data['matches'].append(int(matches_tokens[-1]))
        if "configured minimum match count" in line:
            stacking_data['req_matches'].append(int(tokenize(line)[-1]))
        if "Image matching vs ref" in line:
            stacking_data['accepted'].append(bool(tokenize(line)[-1] == "Accepted"))
    write_csv("stacking_data", out_folder, stacking_data)


def write_csv(file_name, out_folder, data_dict):
    lines = [list(data_dict.keys())]
    for i in range(1, max([len(data_dict[s]) for s in data_dict.keys()])):
        lines.append(
            [serie[i] if len(serie) > i else "" for serie in [data_dict[col] for col in data_dict.keys()]])
    dest_path = Path(out_folder).joinpath(f"{file_name}.csv")
    with open(dest_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=';')
        csv_writer.writerows(lines)
    print(f"report {str(dest_path):<35} OK")


def extract_thread_timings(timings):
    MAIN = "MainThread"
    OTHERS = "Others"

    whole = {MAIN: 0., OTHERS: 0.}
    for timing in timings:
        tokens = tokenize(timing)
        if tokens[5] == 'QueueConsumer.run()':
            continue
        key = MAIN if tokens[2] == MAIN else OTHERS
        whole[key] += float(tokens[-2])

    return whole


def extract_function_timings(timings):
    whole = dict()
    for family in timing_families.keys():
        function_timings = dict()

        for ret in timings:
            tokens = tokenize(ret)

            function_name = tokens[5]
            execution_time = float(tokens[-2])

            for target_function in timing_families[family]:
                if function_name == target_function:
                    if function_name in function_timings.keys():
                        function_timings[function_name].append(execution_time)
                    else:
                        function_timings[function_name] = [execution_time]

        whole[family] = (dict(filter(timing_functions_filter, function_timings.items())))

    return whole


def write_timings_csv_files(data: dict, out_folder):
    for family in data.keys():

        series = list()
        for function in data[family].keys():
            serie = list()
            serie.append(function)
            serie.append(data[family][function])
            series.append(serie)

        max_pp_length = max([len(pplist[1]) for pplist in series])

        out_file_name = f"timings_{family}.csv"
        dest_path = Path(out_folder).joinpath(out_file_name)
        with open(dest_path, 'w', newline='') as csv_file:

            csv_writer = csv.writer(csv_file, delimiter=';')

            csv_writer.writerow([
                pplist[0].replace('.process_image()', '')
                    .replace('Stacker._', '')
                    .replace('read_disk_image', 'Load')
                    .replace('ImageSaver._', '')
                    .replace('()', '')
                    .replace('save', 'Save')
                    .replace('_image', '')
                    .replace('Auto', '')
                    .replace('Remover', '')
                    .replace('Remove', '')
                    .replace('ColorBalance', 'ColBal')
                    .replace('find_transformation', 'detect')
                for pplist in series])

            for i in range(max_pp_length):
                current_row = [pplist[1][i] if len(pplist[1]) > i else "" for pplist in series]
                csv_writer.writerow(current_row)

            print(f"report {str(dest_path):<35} OK")


def tokenize(line):
    return re.split("\\s+", line)


def build_timing_candidates():
    for family in timing_families.keys():
        _timing_candidates.extend(timing_families[family])


def timing_functions_filter(pair):
    k, v = pair
    return k in _timing_candidates


if __name__ == '__main__':
    build_timing_candidates()
    main()
