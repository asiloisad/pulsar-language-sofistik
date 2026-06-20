"""
SOFiSTiK Error File Parser
Parses .err files and extracts commands to JSON files.

Supports versioned extraction:
- Processes each version folder (2018, 2020, 2022, 2023, 2024, 2025, 2026)
- Outputs to commands/sofistik.{version}.{lang}.json

.err file format:
- Header: 0000MODULE_NAME SOFiSTiK AG ...
- Command definitions: -10 (German), -20 (English), -*0 (shared)
  - First 4 chars after prefix = command name
  - Following tokens = parameters/keywords
  - Quoted tokens like "MOD " indicate enum parameters
- Enum value lines: -11N/-21N (German/English enum values for Nth parameter)
  - -111 = German enums for 1st quoted param
  - -211 = English enums for 1st quoted param
  - -112 = German enums for 2nd quoted param, etc.

JSON output structure (flat with enums):
{
  "MODULE": {
    "COMMAND": {
      "MOD": ["SECT", "BEAM", ...],   // enum param with values
      "RMOD": ["ACCU", "SING", ...],  // enum param with values
      "LCR": [],                       // regular keyword (empty array)
      "ZGRP": []                       // regular keyword (empty array)
    }
  }
}
"""

import os ; __file__ = os.path.abspath('')+'/extract.py'

import re
import json
from pathlib import Path
from collections import defaultdict

def parse_err_file(filepath):
    """
    Parse a single .err file and extract commands with enum support.

    Returns:
        dict with module info and commands
    """
    result = {
        'module': '',
        'version': '',
        'commands': {}
    }

    # Try different encodings
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        print(f"    Warning: Could not decode {filepath}")
        return result

    if not lines:
        return result

    # Parse header line (first line)
    header_match = re.match(r'^0000(\w+)\s+SOFiSTiK', lines[0])
    if header_match:
        result['module'] = header_match.group(1)

    # Parse version line (second line)
    if len(lines) > 1:
        version_match = re.match(r'^0000VERSION\s+(\d+)', lines[1])
        if version_match:
            result['version'] = version_match.group(1)

    # Parse command definitions
    current_command_key = None
    current_enum_params_de = []  # List of enum param names for German
    current_enum_params_en = []  # List of enum param names for English
    # Track ALL params by position (1-based) for position-based enum value lookup.
    # XXXX placeholder tokens count as position slots but are not stored in the map.
    current_params_by_pos_de = {}  # position -> param_name (real params only)
    current_params_by_pos_en = {}  # position -> param_name (real params only)
    current_total_pos_de = 0      # total allocated positions including XXXX placeholders
    current_total_pos_en = 0      # total allocated positions including XXXX placeholders

    for line in lines:
        line = line.rstrip()

        # Match command definition: -10=CMD or -10 CMD or -*0=CMD or -*0 CMD
        # After command name: space, quote, or ! (e.g., GRP2'NR, TRAI!TYPE)
        cmd_match = re.match(r'^-(10|20|\*0)(=|\s)([A-Z][A-Z0-9]{0,3})(?=[\s\'"!]|$)(.*)$', line, re.IGNORECASE)
        if cmd_match:
            lang_code = cmd_match.group(1)
            cmd_name = cmd_match.group(3).upper()
            rest = cmd_match.group(4)

            # Extract all parameters in order, preserving their types
            all_params = extract_all_params(rest)

            # Build enum_params list (needed for enum value line processing)
            enum_params = [p for p, ptype in all_params if ptype == 'enum']

            if lang_code == '*0':
                # Shared command - same name in both languages
                current_command_key = cmd_name
                current_enum_params_de = enum_params.copy()
                current_enum_params_en = enum_params.copy()
                # Build position map: XXXX placeholders count toward position indices
                # but are not stored as real params.
                current_params_by_pos_de = {i+1: p for i, (p, pt) in enumerate(all_params) if pt != 'placeholder'}
                current_params_by_pos_en = {i+1: p for i, (p, pt) in enumerate(all_params) if pt != 'placeholder'}
                current_total_pos_de = len(all_params)
                current_total_pos_en = len(all_params)

                if cmd_name not in result['commands']:
                    result['commands'][cmd_name] = {
                        'de': cmd_name,
                        'en': cmd_name,
                        'params_de': {},  # param_name -> set of enum values (empty for regular keywords)
                        'params_en': {}
                    }
                # Add all real params in order with empty sets
                for param_name, param_type in all_params:
                    if param_type == 'placeholder':
                        continue
                    if param_name not in result['commands'][cmd_name]['params_de']:
                        result['commands'][cmd_name]['params_de'][param_name] = set()
                    if param_name not in result['commands'][cmd_name]['params_en']:
                        result['commands'][cmd_name]['params_en'][param_name] = set()

            elif lang_code == '10':
                # German command - start new command pair
                current_command_key = cmd_name
                current_enum_params_de = enum_params.copy()
                current_enum_params_en = []
                # Build position map (XXXX counted as slots, not stored)
                current_params_by_pos_de = {i+1: p for i, (p, pt) in enumerate(all_params) if pt != 'placeholder'}
                current_params_by_pos_en = {}
                current_total_pos_de = len(all_params)
                current_total_pos_en = 0

                if cmd_name not in result['commands']:
                    result['commands'][cmd_name] = {
                        'de': cmd_name,
                        'en': cmd_name,
                        'params_de': {},
                        'params_en': {}
                    }
                # Add all real params in order
                for param_name, param_type in all_params:
                    if param_type == 'placeholder':
                        continue
                    if param_name not in result['commands'][cmd_name]['params_de']:
                        result['commands'][cmd_name]['params_de'][param_name] = set()

            elif lang_code == '20':
                # English command - links to previous German command
                if current_command_key and current_command_key in result['commands']:
                    result['commands'][current_command_key]['en'] = cmd_name
                    current_enum_params_en = enum_params.copy()
                    # Build position map (XXXX counted as slots, not stored)
                    current_params_by_pos_en = {i+1: p for i, (p, pt) in enumerate(all_params) if pt != 'placeholder'}
                    current_total_pos_en = len(all_params)
                    # Add all real params in order
                    for param_name, param_type in all_params:
                        if param_type == 'placeholder':
                            continue
                        if param_name not in result['commands'][current_command_key]['params_en']:
                            result['commands'][current_command_key]['params_en'][param_name] = set()
                else:
                    # No German predecessor
                    current_command_key = cmd_name
                    current_enum_params_de = []
                    current_enum_params_en = enum_params.copy()
                    # Build position map (XXXX counted as slots, not stored)
                    current_params_by_pos_de = {}
                    current_params_by_pos_en = {i+1: p for i, (p, pt) in enumerate(all_params) if pt != 'placeholder'}
                    current_total_pos_de = 0
                    current_total_pos_en = len(all_params)
                    if cmd_name not in result['commands']:
                        result['commands'][cmd_name] = {
                            'de': cmd_name,
                            'en': cmd_name,
                            'params_de': {},
                            'params_en': {}
                        }
                    # Add all real params in order
                    for param_name, param_type in all_params:
                        if param_type == 'placeholder':
                            continue
                        if param_name not in result['commands'][cmd_name]['params_en']:
                            result['commands'][cmd_name]['params_en'][param_name] = set()
            continue

        # Match enum value lines: -111, -*1A, -*1B, -*1G, -*1K, -211, etc.
        # Format: -XYZ  X=language (1=DE, 2=EN, *=shared)  Y=group (usually 1)
        # Z encodes the target parameter:
        #   1-9       → position 1-9
        #   A-F (hex) → position 10-15
        #   G-J       → position 16-19  (extended beyond hex)
        #   K-Z       → enum param INDEX  (K=0, L=1, M=2 ...)
        enum_match = re.match(r'^-(1|2|\*)([0-9A-Fa-f])([0-9A-Za-z])\s+(.*)$', line)
        if enum_match and current_command_key and current_command_key in result['commands']:
            lang_prefix = enum_match.group(1)
            middle_digit = enum_match.group(2)
            last_char = enum_match.group(3).upper()
            rest = enum_match.group(4).strip()

            if rest:
                # Skip lines with version/compatibility markers or cross-reference redirects.
                # Individual '....' tokens are filtered later by extract_keys, so no line-level skip needed.
                if re.search(r'\bF\d{2}\b', rest) or '->' in rest:
                    continue
                enum_values = extract_keys(rest)

                # Determine lookup method: position-based or enum-index-based
                use_position_lookup = False
                param_position = None
                enum_param_idx = None

                if last_char in 'KLMNOPQRSTUVWXYZ':
                    # K-Z: enum parameter INDEX (K=0, L=1, M=2 ...)
                    enum_param_idx = ord(last_char) - ord('K')
                elif last_char in 'GHIJ':
                    # G-J: positions 16-19, extending beyond hex F=15
                    param_position = ord(last_char) - ord('G') + 16
                    use_position_lookup = True
                else:
                    # 1-9 and A-F: parameter POSITION via hex (A=10 ... F=15)
                    try:
                        param_position = int(last_char, 16)
                        use_position_lookup = True
                    except ValueError:
                        # Unknown character — skip
                        continue

                if lang_prefix == '1' or lang_prefix == '*':
                    if use_position_lookup and param_position in current_params_by_pos_de:
                        param_name = current_params_by_pos_de[param_position]
                        if param_name in result['commands'][current_command_key]['params_de']:
                            result['commands'][current_command_key]['params_de'][param_name].update(enum_values)
                    elif enum_param_idx is not None and 0 <= enum_param_idx < len(current_enum_params_de):
                        param_name = current_enum_params_de[enum_param_idx]
                        if param_name in result['commands'][current_command_key]['params_de']:
                            result['commands'][current_command_key]['params_de'][param_name].update(enum_values)

                if lang_prefix == '2' or lang_prefix == '*':
                    if use_position_lookup and param_position in current_params_by_pos_en:
                        param_name = current_params_by_pos_en[param_position]
                        if param_name in result['commands'][current_command_key]['params_en']:
                            result['commands'][current_command_key]['params_en'][param_name].update(enum_values)
                    elif enum_param_idx is not None and 0 <= enum_param_idx < len(current_enum_params_en):
                        param_name = current_enum_params_en[enum_param_idx]
                        if param_name in result['commands'][current_command_key]['params_en']:
                            result['commands'][current_command_key]['params_en'][param_name].update(enum_values)
            continue

        # Match documentation lines with bracket enums: -17 CMD [A|B|C] description...
        # -17 = German, -27 = English, -*7 = shared (both languages)
        # These lines contain help text, NOT parameter definitions.
        # Only extract bracket enums [A|B|C] for the OPT parameter.
        doc_match = re.match(r'^-(\*7|17|27)\s+([A-Z]{1,4})\s+(.*)$', line, re.IGNORECASE)
        if doc_match and current_command_key and current_command_key in result['commands']:
            lang_code = doc_match.group(1)
            rest = doc_match.group(3)

            # Extract bracket enums [A|B|C|...] only (not regular text!)
            bracket_enums = extract_bracket_enums(rest)

            if lang_code in ('17', '*7'):
                # German / shared — if OPT param exists, add bracket enums to it
                if 'OPT' in result['commands'][current_command_key]['params_de']:
                    result['commands'][current_command_key]['params_de']['OPT'].update(bracket_enums)

            if lang_code in ('27', '*7'):
                # English / shared — if OPT param exists, add bracket enums to it
                if 'OPT' in result['commands'][current_command_key]['params_en']:
                    result['commands'][current_command_key]['params_en']['OPT'].update(bracket_enums)
            continue

        # Match continuation/parameter lines for current command
        param_match = re.match(r'^-(10|20|\*0)\s{2,}(.+)$', line)
        if not param_match:
            param_match = re.match(r'^-(1[0-9A-Z]|2[0-9A-Z]|\*[0-9A-Z])\s+(.*)$', line, re.IGNORECASE)

        if param_match and current_command_key and current_command_key in result['commands']:
            lang_code = param_match.group(1)
            rest = param_match.group(2).strip() if param_match.group(2) else ''

            # Skip if this looks like an enum line (already handled above)
            if re.match(r'^(1|2|\*)[0-9A-Fa-f][0-9A-Za-z]$', lang_code):
                continue

            if rest:
                # Extract all params with type info to track enum params.
                # Placeholders (XXXX) are included to keep position indices correct.
                all_params = extract_all_params(rest)
                enum_params = [p for p, ptype in all_params if ptype == 'enum']

                if lang_code.startswith('1') or lang_code.startswith('*'):
                    current_enum_params_de.extend(enum_params)
                    # start_pos uses the running total (including XXXX slots) so that
                    # placeholders in previous blocks don't shift positions here.
                    start_pos = current_total_pos_de + 1
                    current_total_pos_de += len(all_params)
                    for i, (param_name, param_type) in enumerate(all_params):
                        if param_type == 'placeholder':
                            continue
                        current_params_by_pos_de[start_pos + i] = param_name
                        if param_name not in result['commands'][current_command_key]['params_de']:
                            result['commands'][current_command_key]['params_de'][param_name] = set()

                if lang_code.startswith('2') or lang_code.startswith('*'):
                    current_enum_params_en.extend(enum_params)
                    start_pos = current_total_pos_en + 1
                    current_total_pos_en += len(all_params)
                    for i, (param_name, param_type) in enumerate(all_params):
                        if param_type == 'placeholder':
                            continue
                        current_params_by_pos_en[start_pos + i] = param_name
                        if param_name not in result['commands'][current_command_key]['params_en']:
                            result['commands'][current_command_key]['params_en'][param_name] = set()
            continue

    # Convert sets to sorted lists for JSON serialization (empty sets become null)
    for cmd_data in result['commands'].values():
        cmd_data['params_de'] = {k: sorted(list(v)) if v else None for k, v in cmd_data['params_de'].items()}
        cmd_data['params_en'] = {k: sorted(list(v)) if v else None for k, v in cmd_data['params_en'].items()}

    return result


def extract_keys(text):
    """
    Extract keyword tokens from a parameter line.
    Keywords are up to 4 alphanumeric characters.
    Excludes text in parentheses (documentation/comments).
    Returns list preserving order of first occurrence.
    """
    keys = []
    seen = set()

    # Remove text in parentheses (documentation text)
    text = re.sub(r'\([^)]*\)', '', text)

    # Remove bracketed enum lists [A|B|C] - these are parsed separately
    text = re.sub(r'\[[^\]]*\]', '', text)

    # Strip backtick prefix from tokens (comment markers like `CMNT -> CMNT)
    # These are still valid parameters for syntax highlighting
    text = re.sub(r'`([A-Z]+)', r'\1', text, flags=re.IGNORECASE)

    # Match tokens: 1-4 chars, may contain underscore (e.g., ST_M, QU_M)
    tokens = re.findall(r"['\"`=]?([A-Z][A-Z0-9_]{0,3})(?![A-Z0-9_])", text, re.IGNORECASE)

    for token in tokens:
        token = token.upper()
        if token in ('XXXX', '....', 'NONE'):
            continue
        if re.match(r'^\d+$', token):
            continue
        if re.match(r'^\d{4}$', token):
            continue
        if token not in seen:
            keys.append(token)
            seen.add(token)

    return keys


def extract_all_params(text):
    """
    Extract all parameters from a line, preserving order.
    Returns a list of tuples: (param_name, param_type)
    where param_type is 'enum' ("), 'literal' ('), or 'keyword' (regular).
    """
    params = []
    seen = set()

    # Remove text in parentheses (documentation text)
    text = re.sub(r'\([^)]*\)', '', text)

    # Remove bracketed enum lists [A|B|C] - these are parsed separately
    text = re.sub(r'\[[^\]]*\]', '', text)

    # Find all tokens with their prefixes, preserving order
    # Pattern matches: optional prefix (" ' ` = !) followed by 1-4 chars (may include underscore)
    for match in re.finditer(r'(["\' `=!]?)([A-Z][A-Z0-9_]{0,3})(?![A-Z0-9_])', text, re.IGNORECASE):
        prefix = match.group(1)
        token = match.group(2).upper()

        if token in ('XXXX', '....', 'NONE'):
            # Placeholder — counts as a position slot but is not a real parameter.
            # Do NOT add to `seen` so that multiple XXXX occurrences are each counted.
            params.append((token, 'placeholder'))
            continue
        if re.match(r'^\d+$', token):
            continue
        if re.match(r'^\d{4}$', token):
            continue
        if token in seen:
            continue

        seen.add(token)

        if prefix == '"':
            params.append((token, 'enum'))
        elif prefix == "'":
            params.append((token, 'literal'))
        elif prefix == '`':
            params.append((token, 'comment'))
        else:
            params.append((token, 'keyword'))

    return params


def extract_bracket_enums(text):
    """
    Extract enum values from bracket notation [A|B|C|...].
    Used in documentation lines (-17/-27).
    """
    enums = set()
    bracket_match = re.search(r'\[([^\]]+)\]', text)
    if bracket_match:
        content = bracket_match.group(1)
        # Split by | and extract valid tokens
        for item in content.split('|'):
            item = item.strip().upper()
            if item and re.match(r'^[A-Z][A-Z0-9]{0,3}$', item):
                if item not in ('XXXX', '....', 'NONE'):
                    enums.add(item)
    return enums


def parse_all_err_files(errs_dir):
    """Parse all .err files in a directory."""
    all_commands = {}

    # Module name aliases: older versions used truncated 4-char names in headers
    # (e.g., MAXI instead of MAXIMA). Normalize to canonical names.
    MODULE_ALIASES = {
        'DBIN': 'DBINFO',
        'MAXI': 'MAXIMA',
        'TEMP': 'TEMPLATE',
    }

    errs_path = Path(errs_dir)
    for err_file in sorted(errs_path.glob('*.err')):
        print(f"  Parsing {err_file.name}...")
        data = parse_err_file(err_file)

        module_name = data['module'] or err_file.stem.upper()
        module_name = MODULE_ALIASES.get(module_name, module_name)

        if data['commands']:
            all_commands[module_name] = data['commands']

    return all_commands


def process_version(version, build_dir, output_dir):
    """Process a single version's .err files and output JSON files."""
    errs_dir = build_dir / version
    if not errs_dir.exists():
        print(f"  Skipping {version} - directory not found")
        return None

    print(f"\nProcessing version {version}...")

    all_commands = parse_all_err_files(errs_dir)

    if not all_commands:
        print(f"  No commands found for {version}")
        return None

    # Calculate statistics
    total_modules = len(all_commands)
    total_commands = sum(len(m) for m in all_commands.values())
    total_params_de = sum(
        len(cmd['params_de'])
        for module in all_commands.values()
        for cmd in module.values()
    )
    total_params_en = sum(
        len(cmd['params_en'])
        for module in all_commands.values()
        for cmd in module.values()
    )
    total_enums_de = sum(
        sum(len(v) for v in cmd['params_de'].values() if v is not None)
        for module in all_commands.values()
        for cmd in module.values()
    )
    total_enums_en = sum(
        sum(len(v) for v in cmd['params_en'].values() if v is not None)
        for module in all_commands.values()
        for cmd in module.values()
    )

    print(f"  {total_modules} modules, {total_commands} commands")
    print(f"  {total_params_de} DE params, {total_params_en} EN params")
    print(f"  {total_enums_de} DE enum values, {total_enums_en} EN enum values")

    # Build separate German and English command structures
    commands_de = {}
    commands_en = {}

    for module_name, commands in all_commands.items():
        commands_de[module_name] = {}
        commands_en[module_name] = {}

        for cmd_key, cmd_data in commands.items():
            de_name = cmd_data['de']
            en_name = cmd_data['en']

            # Flat structure: { "PARAM": [...enum values...] or [] }
            commands_de[module_name][de_name] = cmd_data['params_de']
            commands_en[module_name][en_name] = cmd_data['params_en']

    # Get SOFISTIK module (contains full command definitions)
    # Commands in other modules with empty params inherit from SOFISTIK
    sofistik_de = all_commands.get('SOFISTIK', {})
    sofistik_en_lookup = {}  # en_name -> params_en
    for _, cmd_data in sofistik_de.items():
        sofistik_en_lookup[cmd_data['en']] = cmd_data['params_en']

    # Fill empty commands with params from SOFISTIK module
    # This handles "reference" commands like `-20=SSLA` in aqua.err
    # Track which commands were filled and in how many modules
    filled_modules_en = defaultdict(set)  # cmd_name -> set of modules
    filled_modules_de = defaultdict(set)  # cmd_name -> set of modules
    for module_name, commands in commands_en.items():
        if module_name == 'SOFISTIK':
            continue
        for cmd_name, params in commands.items():
            if not params and cmd_name in sofistik_en_lookup:
                full_params = sofistik_en_lookup[cmd_name]
                if full_params:
                    commands[cmd_name] = full_params.copy()
                    filled_modules_en[cmd_name].add(module_name)
    for module_name, commands in commands_de.items():
        if module_name == 'SOFISTIK':
            continue
        for cmd_name, params in commands.items():
            if not params:
                # Look up by German name in SOFISTIK
                sofistik_cmd = sofistik_de.get(cmd_name)
                if sofistik_cmd and sofistik_cmd['params_de']:
                    commands[cmd_name] = sofistik_cmd['params_de'].copy()
                    filled_modules_de[cmd_name].add(module_name)
    if filled_modules_en:
        print(f"  Filled {len(filled_modules_en)} empty commands from SOFISTIK definitions")

    # Remove ALL distributed commands from SOFISTIK before renaming to BASIC
    # Any command that was filled into other modules should be removed from BASIC
    # to avoid duplicates (e.g., CONC should only be in AQUA/FOOTING, not also in BASIC)
    if 'SOFISTIK' in commands_en:
        for cmd_name in filled_modules_en.keys():
            commands_en['SOFISTIK'].pop(cmd_name, None)
    if 'SOFISTIK' in commands_de:
        for cmd_name in filled_modules_de.keys():
            commands_de['SOFISTIK'].pop(cmd_name, None)
    if filled_modules_en:
        print(f"  Removed {len(filled_modules_en)} distributed commands from SOFISTIK")

    # Rename SOFISTIK module to BASIC
    # BASIC contains common commands like NORM, PROJ, HEAD, etc.
    # that work across all SOFiSTiK programs
    # Grammar builder will include BASIC in each module's scope
    if 'SOFISTIK' in commands_de:
        commands_de['BASIC'] = commands_de.pop('SOFISTIK')
        print(f"  Renamed SOFISTIK to BASIC ({len(commands_de['BASIC'])} commands)")
    if 'SOFISTIK' in commands_en:
        commands_en['BASIC'] = commands_en.pop('SOFISTIK')

    # Add empty TEMPLATE module
    # TEMPLATE is a special prog that allows user-defined commands
    # It needs to exist in JSON for help/autocomplete to recognize it
    if 'TEMPLATE' not in commands_de:
        commands_de['TEMPLATE'] = {}
        commands_en['TEMPLATE'] = {}
        print(f"  Added empty TEMPLATE module")

    # Add ECHO command to all modules if not exists
    # ECHO is a universal command that works in all modules
    echo_params = {'OPT': None, 'VAL': None}
    echo_added = 0
    for module_name in commands_de:
        if 'ECHO' not in commands_de[module_name]:
            commands_de[module_name]['ECHO'] = echo_params.copy()
            echo_added += 1
    for module_name in commands_en:
        if 'ECHO' not in commands_en[module_name]:
            commands_en[module_name]['ECHO'] = echo_params.copy()
    if echo_added > 0:
        print(f"  Added ECHO command to {echo_added} modules")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save German commands JSON
    commands_de_file = output_dir / f'sofistik.{version}.de.json'
    print(f"  Writing {commands_de_file.name}...")
    with open(commands_de_file, 'w', encoding='utf-8') as f:
        json.dump(commands_de, f, indent=2, ensure_ascii=False)

    # Save English commands JSON
    commands_en_file = output_dir / f'sofistik.{version}.en.json'
    print(f"  Writing {commands_en_file.name}...")
    with open(commands_en_file, 'w', encoding='utf-8') as f:
        json.dump(commands_en, f, indent=2, ensure_ascii=False)

    # Build and save EN->DE command name mapping
    # Structure: {module: {en_name: de_name}}
    name_mapping = {}
    for module_name, commands in all_commands.items():
        # Handle SOFISTIK -> BASIC rename
        out_module = 'BASIC' if module_name == 'SOFISTIK' else module_name
        name_mapping[out_module] = {}
        for cmd_data in commands.values():
            en_name = cmd_data['en']
            de_name = cmd_data['de']
            if en_name != de_name:
                name_mapping[out_module][en_name] = de_name
        # Remove empty modules
        if not name_mapping[out_module]:
            del name_mapping[out_module]

    mapping_file = output_dir / f'sofistik.{version}.names.json'
    print(f"  Writing {mapping_file.name}...")
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(name_mapping, f, indent=2, ensure_ascii=False)

    return {
        'commands_de': commands_de,
        'commands_en': commands_en,
        'name_mapping': name_mapping,
        'stats': {
            'modules': total_modules,
            'commands': total_commands,
            'params_de': total_params_de,
            'params_en': total_params_en,
            'enums_de': total_enums_de,
            'enums_en': total_enums_en
        }
    }


def main():
    """Main entry point - process all versions."""
    script_dir = Path(__file__).parent
    build_dir = script_dir
    output_dir = script_dir / 'extracted'  # Intermediate files go here

    versions = ['2018', '2020', '2022', '2023', '2024', '2025', '2026']

    print("SOFiSTiK Command Extractor - Versioned")
    print("=" * 50)

    results = {}
    for version in versions:
        result = process_version(version, build_dir, output_dir)
        if result:
            results[version] = result

    # Print summary
    print("\n" + "=" * 50)
    print("Summary:")
    for version, result in results.items():
        stats = result['stats']
        print(f"  {version}: {stats['modules']} modules, {stats['commands']} commands, "
              f"{stats['params_de']} DE / {stats['params_en']} EN params, "
              f"{stats['enums_de']} DE / {stats['enums_en']} EN enums")

    print("\nDone!")

    return results


if __name__ == '__main__':
    main()
