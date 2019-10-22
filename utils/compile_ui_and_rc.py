import subprocess
from pathlib import Path


def main():
    src_folder_path: Path = Path(__file__).parent.parent / "src"
    generated_src_path: Path = src_folder_path / "generated"

    print("Compiling UI files\n" + "=" * 18)
    command = "pyuic5"

    for ui_file in (src_folder_path / "als" / "ui").glob("*.ui"):

        target_file_path = generated_src_path / ui_file.name.replace('.ui', ".py")
        args = f"{ui_file} -o {target_file_path} --import-from={generated_src_path.stem}"
        print(f"Executing command : {command} {args}")
        completed_process = subprocess.run(f"{command} {args}")
        if completed_process.returncode != 0:
            raise RuntimeError(f"UI compilation failed for {ui_file}")

    print("\nCompiling RC files\n" + "=" * 18)
    command = "pyrcc5"

    for rc_file in (src_folder_path / 'resources').glob("*.qrc"):

        target_file_path = generated_src_path / rc_file.name.replace('.qrc', "_rc.py")
        args = f"{rc_file} -o {target_file_path}"
        print(f"Executing command : {command} {args}")
        completed_process = subprocess.run(f"{command} {args}")
        if completed_process.returncode != 0:
            raise RuntimeError(f"RC compilation failed for {rc_file}")


if __name__ == '__main__':
    main()
