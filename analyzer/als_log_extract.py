import re
from argparse import ArgumentParser
from pathlib import Path

import csv

SECTION = "=" * 50
SUB_SECTION = "-" * 50

_timing_candidates = list()

processing_functions = [
    'read_disk_image()',
    "RemoveDark.process_image()",
    'HotPixelRemover.process_image()',
    "Debayer.process_image()",
    "Standardize.process_image()",
    'Stacker._find_transformation()',
    'Stacker._apply_transformation()',
    'Stacker._align_image()',
    'Stacker._stack_image()',
    "AutoStretch.process_image()",
    "Levels.process_image()",
    "ColorBalance.process_image()",
    "ImageSaver._save_image()"
]


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
        if re.search("^=", line):
            entries.append(buffer)
            buffer = line[1:]
        else:
            buffer += line
    entries.append(buffer)
    print(f'Reassembled {len(entries)} log entries')
    function_returns = list(filter(lambda l: "returned" in l, entries))
    print(f'Collected {len(function_returns)} function returns')

    print(SECTION)
    print("Exporting every function return...")
    print(SUB_SECTION)
    write_csv("global_returns", csv_out_folder, extract_functions_returns(function_returns))

    print(SECTION)
    print("Exporting processing functions timings...")
    print(SUB_SECTION)
    processing_returns = list(filter(lambda l: tokenize(l)[5] in processing_functions, function_returns))
    write_csv("processing_timings", csv_out_folder, extract_functions_returns(processing_returns))

    print(SECTION)
    print("Exporting session data...")
    print(SUB_SECTION)
    write_csv("session", csv_out_folder, extract_session_data(entries))


def extract_functions_returns(function_returns):
    returns_dict = {
        'timestamp': list(),
        'thread': list(),
        'module': list(),
        'name': list(),
        'ret_value': list(),
        'elapsed': list(),
    }
    for ret in function_returns:
        tokens = tokenize(ret)
        returns_dict['timestamp'].append(" ".join(tokens[3:5]))
        returns_dict['thread'].append(tokens[0])
        returns_dict['module'].append(tokens[1])
        returns_dict['name'].append(tokens[5])
        returns_dict['ret_value'].append(tokens[7:-3])
        returns_dict['elapsed'].append(tokens[-2])
    return returns_dict


def extract_session_data(entries):

    session_data = {
        'timestamp': [],
        'type': [],
        'value': [],
    }

    image_translation_match = "\[\s*(\S+)\s+(\S+)\s*\]"

    for line in entries:

        if "*SD-RATIO*" in line:
            extract_float_at_end("ratio", line, session_data)

        elif "*SD-ROT*" in line:
            extract_float_at_end('rotation', line, session_data)

        elif "*SD-TRANS*" in line:
            trans_matcher = re.search(image_translation_match, line)
            session_data['value'].append(float(trans_matcher.group(1)))
            session_data['timestamp'].append(" ".join((tokenize(line)[3:5])))
            session_data['type'].append("x_trans")

            session_data['value'].append(float(trans_matcher.group(2)))
            session_data['timestamp'].append(" ".join((tokenize(line)[3:5])))
            session_data['type'].append("y_trans")

        elif "*SD-SCALE*" in line:
            extract_float_at_end("scale", line, session_data)

        elif "*SD-MATCHES*" in line:
            extract_float_at_end("matches", line, session_data)

        elif "*SD-REQ*" in line:
            extract_float_at_end("req_matches", line, session_data)

        elif "*SD-Q-PRE*" in line:
            extract_float_at_end("q_pre", line, session_data)

        elif "*SD-Q-STA*" in line:
            extract_float_at_end("q_stack", line, session_data)

        elif "*SD-FRMTIME*" in line:
            extract_float_at_end("frm_total", line, session_data)

        elif "*SD-Q-POST*" in line:
            extract_float_at_end("q_post", line, session_data)

        elif "*SD-Q-SAV*" in line:
            extract_float_at_end("q_save", line, session_data)

        elif "*SD-ALIGNOK*" in line:
            session_data['value'].append(1. if (tokenize(line)[-1] == "Accepted") else 0.)
            session_data['timestamp'].append(" ".join((tokenize(line)[3:5])))
            session_data['type'].append("align")

        elif "*SM-MEM*" in line:
            extract_float_at_end("memory", line, session_data)

    return session_data


def extract_float_at_end(event_type, line, data_dict):
    data_dict['value'].append(float(tokenize(line)[-1]))
    data_dict['timestamp'].append(" ".join((tokenize(line)[3:5])))
    data_dict['type'].append(event_type)


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


if __name__ == '__main__':
    main()
