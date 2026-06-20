"""
SOFiSTiK Grammar Builder - Unified Version
Generates a single grammar file that covers all versions (2018-2026) and languages (EN/DE).
Keywords are merged (union) across all version/language JSON files.
"""

import os ; __file__ = os.path.abspath('')+'/build.py'

import json
from collections import defaultdict
from pathlib import Path


def parse_params_list(params_list):
    """
    Parse list params format into {param_name: set(enum_values)}.

    Input:  ["NO", "FCK", ["C20", "C25"], "ALFA"]
    Output: {"NO": set(), "FCK": {"C20", "C25"}, "ALFA": set()}
    """
    result = {}
    i = 0
    while i < len(params_list):
        item = params_list[i]
        if isinstance(item, str):
            # Check if next item is an enum values array
            if i + 1 < len(params_list) and isinstance(params_list[i + 1], list):
                result[item] = set(params_list[i + 1])
                i += 2
            else:
                result[item] = set()
                i += 1
        else:
            i += 1  # Skip unexpected items
    return result


def load_all_keywords():
    """
    Load and union keywords from all per-version JSON files.
    Returns a unified dictionary with all modules, commands, and params.
    """
    script_dir = Path(__file__).parent
    commands_dir = script_dir.parent / 'commands'

    # Unified structure: module -> command -> {param: set(enums)}
    unified = {}

    for json_path in sorted(commands_dir.glob('sofistik.*.??.json')):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for module_name, module_data in data.items():
            if module_name not in unified:
                unified[module_name] = {}

            for cmd_name, params_list in module_data.items():
                if cmd_name not in unified[module_name]:
                    unified[module_name][cmd_name] = {}

                if params_list:
                    parsed = parse_params_list(params_list)
                    for param_name, enum_values in parsed.items():
                        if param_name not in unified[module_name][cmd_name]:
                            unified[module_name][cmd_name][param_name] = set()
                        unified[module_name][cmd_name][param_name].update(enum_values)

    # Convert sets back to sorted lists (or None if empty)
    for module_name in unified:
        for cmd_name in unified[module_name]:
            for param_name in unified[module_name][cmd_name]:
                enum_set = unified[module_name][cmd_name][param_name]
                unified[module_name][cmd_name][param_name] = sorted(enum_set) if enum_set else None

    return unified


def escape_regex(text):
    """
    Escape special regex characters in text.
    For CSON files, we need double backslashes (\\).

    Args:
        text: String to escape

    Returns:
        Escaped string safe for use in regex patterns
    """
    # Characters that need escaping in regex
    special_chars = r'\.^$*+?{}[]()|\-'
    result = ""
    for char in text:
        if char in special_chars:
            result += "\\\\" + char  # Double backslash for CSON
        else:
            result += char
    return result


def has_special_chars(text):
    """Check if text contains regex special characters that need escaping."""
    special_chars = r'\.^$*+?{}[]()|\-'
    return any(char in special_chars for char in text)


def optimize_pattern(keyword_list):
    """
    Create optimized regex pattern by grouping keywords by first character.
    This reduces backtracking and improves matching performance.

    Keywords with special regex characters are NOT grouped for safety.

    Args:
        keyword_list: List of keywords to optimize into a regex pattern

    Returns:
        Optimized regex pattern string
    """
    if not keyword_list:
        return ""

    # Separate keywords with special chars from regular ones
    special_keywords = [kw for kw in keyword_list if has_special_chars(kw)]
    regular_keywords = [kw for kw in keyword_list if not has_special_chars(kw)]

    # Group regular keywords by their first character (case-insensitive)
    keywords_grouped_by_first_char = defaultdict(list)
    for keyword in regular_keywords:
        first_character = keyword[0].upper()
        keywords_grouped_by_first_char[first_character].append(keyword)

    # Sort within each group by length (longest first) to avoid prefix matching issues
    for character in keywords_grouped_by_first_char:
        keywords_grouped_by_first_char[character].sort(key=lambda x: (-len(x), x))

    # Build optimized pattern for regular keywords
    pattern_parts = []

    for character in sorted(keywords_grouped_by_first_char.keys()):
        word_list = keywords_grouped_by_first_char[character]
        if len(word_list) == 1:
            pattern_parts.append(word_list[0])
        else:
            # Group words with same first character
            word_suffixes = '|'.join(word[1:] for word in word_list)
            pattern_parts.append(f"(?:{character}(?:{word_suffixes}))")

    # Add special keywords individually, escaped and sorted by length (longest first)
    special_keywords.sort(key=lambda x: (-len(x), x))
    for keyword in special_keywords:
        pattern_parts.append(escape_regex(keyword))

    return "|".join(pattern_parts)


def generate_module_patterns(keywords_data):
    """
    Generate optimized pattern blocks for each SOFiSTiK module.
    NOW PROPERLY SCOPES SUBKEYWORDS TO THEIR PARENT COMMANDS.
    Scope continues across ALL lines until another command or semicolon.
    BASIC commands are included in every module's scope.

    Args:
        keywords_data: Dictionary of modules and their keywords

    Returns:
        Tuple of (module_pattern_list, repository_pattern_list)
    """
    module_begin_end_patterns = []
    module_repository_patterns = []

    # Get BASIC commands to include in every module
    basic_commands = keywords_data.get('BASIC', {})

    for module_name, module_commands in keywords_data.items():
        if module_name == 'BASIC':
            continue

        module_name_lowercase = module_name.lower()

        # Generate module begin/end pattern for PROG statements
        module_begin_end_patterns.append(f'''
  {{
  begin: '(?i)^[ \\\\t]*([\\\\$\\\\+-]?PROG)( +{module_name})( .*)?$'
  beginCaptures:
    1: name: 'support.class.{module_name_lowercase}.sofistik'
    2: name: 'support.class.{module_name_lowercase}.sofistik'
    3:
      name: 'comment.line.{module_name_lowercase}.sofistik'
      patterns: [{{ include: 'text.todo' }}]
  end: '(?i)(?=^[ \\\\t]*[\\\\$\\\\+-]?PROG\\\\b)'
  name: 'module.{module_name_lowercase}.sofistik'
  patterns: [
    {{'include': '#{module_name}'}}
    ]
  }}''')

        # Collect all commands for this module (including BASIC commands)
        # Merge module-specific commands with BASIC commands
        combined_commands = {**basic_commands, **module_commands}
        all_module_commands = list(combined_commands.keys())

        # Sort by length (longest first) to prevent prefix matching issues
        sorted_commands = sorted(all_module_commands, key=lambda x: (-len(x), x))

        # Generate optimized regex pattern for all commands - to use in the end pattern
        commands_regex_pattern = optimize_pattern(sorted_commands)

        # Build repository entry with command-specific subkeyword scoping
        repository_entry = f'''
  {module_name}: {{
    patterns: [
      {{ include: '#preprocessorDefine' }}'''

        # Generate a begin/end pattern for EACH command with its specific subkeywords
        # This includes both module-specific commands and BASIC commands
        for command_name, command_params in combined_commands.items():
            # command_params is now a dict: {"PARAM": [enum_values] or null}
            # Extract parameter names as subkeywords
            command_subkeywords = list(command_params.keys()) if command_params else []

            if command_subkeywords:  # Only if command has subkeywords
                # Sort subkeywords by length (longest first)
                sorted_subkeywords = sorted(command_subkeywords, key=lambda x: (-len(x), x))
                subkeywords_regex_pattern = optimize_pattern(sorted_subkeywords)

                # Create a scoped pattern for this command and its subkeywords
                # The scope continues across ALL lines until:
                # 1. Another command from this module appears (at line start or after semicolon)
                # 2. A semicolon is encountered (ends current command)
                # 3. A new PROG statement (which ends the module scope)

                # Build patterns list - only params (enum highlighting removed - use tree-sitter for that)
                patterns_content = f'''
          {{
            match: '(?i)(?<!\\\\w)({subkeywords_regex_pattern})(?!\\\\w)'
            name: 'entity.name.function.sofistik'
          }}'''

                repository_entry += f'''
      {{
        begin: '(?i)(?:^[ \\\\t]*|(;) *)({command_name})(?=;|$| )'
        beginCaptures:
          1: name: 'support.type.sofistik'
          2: name: 'keyword.control.sofistik'
        end: '(?i)(?=(?:^[ \\\\t]*|; *)(?:{commands_regex_pattern})|;|^[ \\\\t]*[\\\\$\\\\+-]?PROG\\\\b)'
        patterns: [{patterns_content}
          {{ include: '#normalText' }}
        ]
      }}'''
            else:
                # Command without subkeywords - just match it directly
                repository_entry += f'''
      {{
        match: '(?i)(?:^[ \\\\t]*|(;) *)({command_name})(?=;|$| )'
        captures:
          1: name: 'support.type.sofistik'
          2: name: 'keyword.control.sofistik'
      }}'''

        # Close the repository entry
        repository_entry += '''
      { include: '#normalText' }
    ]
  }'''

        module_repository_patterns.append(repository_entry)

    return module_begin_end_patterns, module_repository_patterns


def generate_grammar(keywords_data, version=None, language=None):
    """
    Generate complete optimized CSON grammar file.

    Args:
        keywords_data: Dictionary of modules and their keywords
        version: Optional version string (e.g., '2026')
        language: Optional language code (e.g., 'en', 'de')

    Returns:
        Complete grammar as string
    """
    module_patterns, repository_patterns = generate_module_patterns(keywords_data)

    # Build scope name and display name based on version/language
    if version and language:
        scope_name = f'source.sofistik.{version}.{language}'
        display_name = f'SOFiSTiK {version} ({language.upper()})'
        # Versioned grammars don't auto-match file types
        file_types_line = "fileTypes: []"
    else:
        scope_name = 'source.sofistik'
        display_name = 'SOFiSTiK'
        file_types_line = "fileTypes: ['dat','gra','grb','results']"

    # Grammar header with metadata and references
    grammar_header = f'''
# ***** References *****
# https://pulsar-edit.dev/docs/launch-manual/sections/core-hacking/#creating-a-legacy-textmate-grammar
# https://gist.github.com/savetheclocktower/c9607b97477d4817911e4f2f8db89679
# http://manual.macromates.com/en/language_grammars/
# https://github.com/kkos/oniguruma/blob/master/doc/RE
# https://regex101.com/

scopeName: '{scope_name}'
name: '{display_name}'
{file_types_line}
patterns: [
  {{
    match: '(?i)^@ *SOFiSTiK *(\\\\d{{4}})(-\\\\d\\\\d?)? *$'
    name: 'meta.version.sofistik'
  }}
  {{
    match: '(?i)^@ .+'
    name: 'meta.sofistik'
  }}
  {{ include: '#normalText' }}
'''

    # Add module-specific patterns
    grammar_with_modules = grammar_header + ''.join(module_patterns)

    # Repository with base patterns for common SOFiSTiK syntax
    repository_base_patterns = r'''
]
repository:
  normalText: {
    patterns: [
      { include: '#textCommands' }
      { include: '#preprocessorDefine' }
      { include: '#preprocessorInclude' }
      { include: '#preprocessorApplyAndSys' }
      { include: '#preprocessorConditional' }
      { include: '#dollarVariableReference' }
      { include: '#textBlock' }
      { include: '#comments' }
      { include: '#stringDoubleQuoted' }
      { include: '#stringSingleQuoted' }
      { include: '#variableCommands' }
      { include: '#hashVariableReference' }
      { include: '#loopKeyword' }
      { include: '#controlFlowKeywords' }
      { include: '#expressionWithEquals' }
      { include: '#units' }
    ]
  }
  textCommands: {
    match: '(?i)(^[ \\t]*)(HEAD|TXB|TXE)( .+?$| *$)'
    captures:
      1: name: 'support.type.sofistik'
      2: name: 'keyword.control.sofistik'
  }
  textBlock: {
    begin: '(?i)^[ \\t]*(<TEXT>|<TEXT,FILE=\\+?(.+)>)(?= |$)'
    beginCaptures:
      1: name: 'support.function.sofistik'
      2: name: 'string.other.sofistik'
    end: '(?i)^[ \\t]*(<\\/TEXT>)(?= |$)'
    endCaptures:
      1: name: 'support.function.sofistik'
    patterns: [
      { include: '#dollarVariableReference' }
      { include: '#hashVariableReference' }
      { include: '#editBlock' }
    ]
  }
  editBlock: {
    begin: '(?i)(<EDIT:.+?>)'
    beginCaptures:
      1: name: 'support.function.sofistik'
    end: '(?i)(<\\/EDIT>)'
    endCaptures:
      1: name: 'support.function.sofistik'
    patterns: [
      { include: '#hashVariableReference' }
      { include: '#dollarVariableReference' }
    ]
  }
  preprocessorDefine: {
    match: '(?i)^[ \\t]*(#DEFINE|#ENDDEF) *(.+?)?(?: *= *(.*))?$'
    captures:
      1: name: 'entity.name.section.sofistik'
      2: name: 'string.other.sofistik'
      3: patterns: [
        { include: '#dollarVariableReference' }
        { include: '#comments' }
        { include: '#stringDoubleQuoted' }
        { include: '#stringSingleQuoted' }
        { include: '#variableCommands' }
        { include: '#hashVariableReference' }
        { include: '#loopKeyword' }
        { include: '#controlFlowKeywords' }
        { include: '#expressionWithEquals' }
        { include: '#units' }
      ]
      4: name: 'entity.name.section.sofistik'
  }
  preprocessorInclude: {
    match: '(?i)^[ \\t]*(#INCLUDE) +(.+)'
    captures:
      1: name: 'entity.name.section.sofistik'
      2:
        name: 'string.other.sofistik'
        patterns: [{ include: '#dollarVariableReference' }]
  }
  preprocessorApplyAndSys: {
    match: '(?i)^[ \\t]*([\\$\\+-]?APPLY|[\\+-]?SYS)( +.+)'
    captures:
      1: name: 'support.class.sofistik'
      2:
        name: 'string.other.sofistik'
        patterns: [
          { include: '#dollarVariableReference' }
          { include: '#comments' }
        ]
  }
  preprocessorConditional: {
    match: '(?i)^[ \\t]*(#IF|#ELSE|#ENDIF)'
    captures:
      1: name: 'entity.name.section.sofistik'
  }
  dollarVariableReference: {
    match: '(;)?[ ]*(\\$\\(\\S+?\\))'
    captures:
      1: name: 'support.type.sofistik'
      2: name: 'variable.other.sofistik'
  }
  comments: {
    match: '(?i)(?:!|\\/\\/|\\$(?!PROG))(.*)'
    name: 'comment.line.sofistik'
    captures:
      1: patterns: [{ include: 'text.todo' }]
  }
  stringDoubleQuoted: {
    match: '\\"(.*?)\\"'
    name: 'string.double.sofistik'
    captures:
      1: patterns: [{ include: '#dollarVariableReference' }]
  }
  stringSingleQuoted: {
    match: "\\'(.*?)\\'"
    name: 'string.single.sofistik'
    captures:
      1: patterns: [{ include: '#dollarVariableReference' }]
  }
  variableCommands: {
    match: '(?i)(^|;)[ \\t]*(LET|STO|DEL|DBG|PRT)(?!\\w)'
    captures:
      1: name: 'support.type.sofistik'
      2: name: 'keyword.control.sofistik'
  }
  hashVariableReference: {
    match: '(#\\w+|#\\(\\w+(?:,\\d\\.\\d)?\\))'
    name: 'variable.other.sofistik'
  }
  loopKeyword: {
    match: '(?i)(^|;)[ \\t]*(LOOP)(?!\\w)'
    captures:
      1: name: 'support.type.sofistik'
      2: name: 'keyword.control.sofistik'
  }
  controlFlowKeywords: {
    match: '(?i)(^|;)[ \\t]*(IF|ELSEIF|ELSE|ENDIF|ENDLOOP|END)(?=\\s|$)'
    captures:
      1: name: 'support.type.sofistik'
      2: name: 'keyword.control.sofistik'
  }
  expressionWithEquals: {
    match: '(?<=\\s|^)(=\\S+)'
    captures:
      1:
        name: 'entity.name.function.sofistik'
        patterns: [{'include': '#hashVariableReference'}]
  }
  units: {
    match: '(?<=\\S)\\[.*?\\]'
    name: 'constant.other.sofistik'
  }
'''

    # Combine all parts: header + modules + repository + module repositories
    complete_grammar = grammar_with_modules + repository_base_patterns + ''.join(repository_patterns)

    return complete_grammar


def build_unified_grammar(grammars_dir):
    """Build a single unified grammar from all version/language JSON files."""
    print("\nBuilding unified grammar (all versions, all languages)...")

    keywords_data = load_all_keywords()

    complete_grammar = generate_grammar(keywords_data)

    # Write unified grammar file
    grammar_path = grammars_dir / 'sofistik.cson'
    with open(grammar_path, 'w', encoding='utf-8') as grammar_file:
        grammar_file.write(complete_grammar[1:] + '\n')  # Remove leading newline

    total_commands = sum(len(module) for module in keywords_data.values())
    total_params = sum(
        len(params)
        for module in keywords_data.values()
        for params in module.values()
        if params
    )

    print(f"  Created {grammar_path.name}:")
    print(f"    {len(keywords_data)} modules")
    print(f"    {total_commands} commands")
    print(f"    {total_params} parameters")

    return {
        'modules': len(keywords_data),
        'commands': total_commands,
        'params': total_params
    }


def main():
    """Main build process - generates unified grammar."""
    script_dir = Path(__file__).parent
    grammars_dir = script_dir.parent / 'grammars'

    print("SOFiSTiK Grammar Builder - Unified")
    print("=" * 50)

    result = build_unified_grammar(grammars_dir)

    print("\n" + "=" * 50)
    print("Build complete!")
    print(f"  Merged all versions (2018-2026) and languages (EN/DE)")
    print(f"  {result['modules']} modules, {result['commands']} commands, {result['params']} params")


if __name__ == '__main__':
    main()
