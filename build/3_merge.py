"""
Convert extracted JSON files to per-version provider-ready files.

Input:  build/extracted/sofistik.{version}.{lang}.json (object params format)
Output: commands/sofistik.{version}.{lang}.json (list params format)
        commands/sofistik.{version}.names.json (EN<->DE name mappings)
        commands/meta.json (versions list)

Per-version output format:
{
  "AQUA": {
    "CONC": ["NO", "FCK", ["C20", "C25"], "ALFA"],
    "HEAD": []
  }
}

Params list format:
- String = param name (no enum values)
- Array after a param name = enum values for that param
- Empty list [] = command exists but has no params
"""

import os ; __file__ = os.path.abspath('')+'/merge.py'

import json
from pathlib import Path


def convert_params(params_obj):
    """
    Convert params from object format to list format.

    Input:  {"NO": null, "FCK": ["C20", "C25"], "ALFA": null}
    Output: ["NO", "FCK", ["C20", "C25"], "ALFA"]
    """
    result = []
    for param_name, enum_values in params_obj.items():
        result.append(param_name)
        if enum_values:
            result.append(sorted(enum_values) if not isinstance(enum_values, list) else enum_values)
    return result


def convert_version(data):
    """
    Convert a single version's extracted data to provider-ready format.

    Input:  { "MODULE": { "CMD": { "PARAM": [...] | null } } }
    Output: { "MODULE": { "CMD": ["PARAM", [...enum], ...] } }
    """
    result = {}
    for module_name, commands in data.items():
        result[module_name] = {}
        for cmd_name, params in commands.items():
            result[module_name][cmd_name] = convert_params(params) if params else []
    return result


def main():
    script_dir = Path(__file__).parent
    extracted_dir = script_dir / 'extracted'
    commands_dir = script_dir.parent / 'commands'

    # Discover versions from extracted files
    versions = sorted(set(
        f.stem.split('.')[1]
        for f in extracted_dir.glob('sofistik.*.en.json')
    ))

    if not versions:
        print("No extracted files found!")
        return

    print(f"Converting {len(versions)} versions: {', '.join(versions)}")

    # Ensure output directory exists
    commands_dir.mkdir(parents=True, exist_ok=True)

    total_size = 0
    total_files = 0

    for ver in versions:
        for lang in ['en', 'de']:
            input_file = extracted_dir / f'sofistik.{ver}.{lang}.json'
            if not input_file.exists():
                continue

            with open(input_file, encoding='utf-8') as f:
                data = json.load(f)

            converted = convert_version(data)

            # Count stats
            total_modules = len(converted)
            total_commands = sum(len(cmds) for cmds in converted.values())

            output_file = commands_dir / f'sofistik.{ver}.{lang}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(converted, f, indent=2, ensure_ascii=False)

            size = output_file.stat().st_size
            total_size += size
            total_files += 1

            print(f"  {output_file.name}: {total_modules} modules, {total_commands} commands ({size/1024:.0f} KB)")

    # Write meta.json
    meta = {
        "versions": versions,
    }
    meta_file = commands_dir / 'meta.json'
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    total_files += 1

    # Remove old merged files if they exist
    for old_file in ['sofistik.en.json', 'sofistik.de.json']:
        old_path = commands_dir / old_file
        if old_path.exists():
            old_path.unlink()
            print(f"  Removed old merged file: {old_file}")

    print(f"\nTotal: {total_files} files, {total_size/1024:.0f} KB")
    print("Done!")


if __name__ == '__main__':
    main()
