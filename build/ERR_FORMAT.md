# SOFiSTiK .err File Format

This document describes the structure of SOFiSTiK `.err` files used to extract command definitions and parameters for syntax highlighting.

## File Structure

Each `.err` file contains command definitions for a SOFiSTiK module. The file consists of:

1. **Header** - Module name and version
2. **Command definitions** - Commands with their parameters
3. **Enum value lines** - Allowed values for enum parameters
4. **Documentation/error messages** - Not used for extraction

## Line Prefixes

All definition lines start with a prefix indicating language and line type:

| Prefix | Description |
|--------|-------------|
| `-10` | German command/parameter definition |
| `-20` | English command/parameter definition |
| `-*0` | Shared (both languages) command/parameter definition |
| `-1XY` | German enum values (X=param index, Y=continuation) |
| `-2XY` | English enum values (X=param index, Y=continuation) |
| `-*XY` | Shared enum values (X=param index, Y=continuation) |
| `-*2` | Data type hints (not used) |

## Command Definition Lines

### Format
```
-10 CMD params...
-20 CMD params...
-*0 CMD params...
```

### Command Name
- 1-4 uppercase letters/digits after the prefix
- Followed by space, `'`, `"`, or `!`

### Examples
```
-10 STAB'VON 'BIS  DELT"TYP  PA   PE
-20 BEAM'FROM'TO   INC "TYPE PA   PE
-20 TRAI!TYPE'P1   P2   P3   P4   P5
-10 GRP2'NR   STEA QUEA QUEX QUEY ALP0
```

## Parameter Types

Parameters are identified by their prefix character:

| Prefix | Type | Description |
|--------|------|-------------|
| `"` | Enum | Parameter with predefined values |
| `'` | Literal | Literal/fixed parameter |
| `` ` `` | Comment | Comment marker (still valid param) |
| `!` | Keyword | Regular keyword parameter |
| (none) | Keyword | Regular keyword parameter |

### Examples
```
"TYPE    → enum parameter (has predefined values)
'FROM    → literal parameter
`TITL    → comment marker
WIDT     → regular keyword
!TYPE    → keyword (! is separator, not prefix)
```

## Continuation Lines

Parameters can span multiple lines. Continuation lines start with the language prefix followed by spaces:

```
-20 TRAI!TYPE'P1   P2   P3   P4   P5   P6   P7   P8   P9   PFAC PFAV
-20      WIDT'PHI 'PHIS V    FUGA XCON YEX "DIR "DIRT
-*0      FRB  DAB  BOGI FRBO DABO WHEE FRWH DAWH
```

## Enum Value Lines

Define allowed values for enum parameters.

### Format
```
-XYZ values...
```

Where:
- `X` = Language: `1` (German), `2` (English), `*` (shared)
- `Y` = Group identifier (usually `1`)
- `Z` = Parameter POSITION (1-based) or enum index letter (K-Z)

Full lookup table for `Z`:

| `Z` value | Meaning |
|-----------|---------|
| `1`–`9` | Position 1–9 |
| `A`–`F` | Position 10–15 (hex) |
| `G`–`J` | Position 16–19 (extended) |
| `K`–`Z` | Enum parameter index (K=0, L=1, M=2 …) |

Named positions with specific semantics: `B`=geometry sub-type, `C`=curve type, `E`=position/reference.

### Position-Based Lookup (digits 1-9, A-J)

The last digit indicates the **parameter position** (1-based) in the command definition:

```
-20 SSLA'EPS  SIG "TYPE TEMP EPST'EPSS"TS   MUET MNOC FCTF
         1    2    3    4    5     6    7    8    9   10  (positions)

-211     SERV ULTI CALC      → position 1 = EPS gets [SERV, ULTI, CALC]
-*13     GPOL GSPL POL SPL   → position 3 = TYPE gets [GPOL, GSPL, POL, SPL]
-*16     SHIF                → position 6 = EPSS gets [SHIF]
-*17     I II I_S II_S       → position 7 = TS gets [I, II, I_S, II_S]
```

### Index-Based Lookup (letters K-Z)

For commands with multiple enum parameters sharing similar values, letters K-Z indicate which **enum parameter** (by index):

```
-*1K     N    R    L    B   → Values for 1st enum param (K=0)
-*1L     N    R    L    B   → Values for 2nd enum param (L=1)
-*1M     X    Y    Z        → Values for 3rd enum param (M=2)
```

### Redirect Lines

Enum lines may contain a cross-reference redirect instead of values:

```
-*1B ->  FACT@XLIT
-21B ->  TORS@CTRL
```

Format: `-> PARAM@COMMAND` — meaning "use enum values from `COMMAND`'s `PARAM` parameter". These are **not** parsed; the redirect is skipped and the enum list remains empty for that parameter.

### Skipped Lines

Lines containing these patterns are not actual enum values:
- `....` - Placeholder markers
- `F18`, `F19`, etc. - Version compatibility flags
- `->` - Cross-reference redirects (see above)

## Parameter Naming

- Parameters are 1-4 characters
- May contain underscores (e.g., `ST_M`, `QU_M`)
- `XXXX` and `....` are placeholders, not real parameters

## Complete Example

```
-10 LZUG!TYP 'P1   P2   P3   P4   P5   P6   P7   P8   P9   PFAK PFAV
-20 TRAI!TYPE'P1   P2   P3   P4   P5   P6   P7   P8   P9   PFAC PFAV
-*2           9999 9999 9999 9999 9999 9999 1001 9999 1001
-10      WIDT'PHI 'PHIS V    FUGA XKOL YEX "DIR "DIRT
-20      WIDT'PHI 'PHIS V    FUGA XCON YEX "DIR "DIRT
-*2      1001           1203      1001 1001
-*0      FRB  DAB  BOGI FRBO DABO WHEE FRWH DAWH
-*1K     N    R    L    B
-*1L     N    R    L    B
```

This defines:
- Command `TRAI` (English) / `LZUG` (German)
- Parameters: `TYPE`, `P1`-`P9`, `PFAC`, `PFAV`, `WIDT`, `PHI`, `PHIS`, `V`, `FUGA`, `XCON`, `YEX`, `DIR`, `DIRT`, `FRB`, `DAB`, `BOGI`, `FRBO`, `DABO`, `WHEE`, `FRWH`, `DAWH`
- Enum `DIR` with values: `N`, `R`, `L`, `B`
- Enum `DIRT` with values: `N`, `R`, `L`, `B`

## Reference Commands

Some `.err` files contain "reference" commands - command names without parameters:

```
-10=ARBL
-20=SSLA
```

These indicate that the command is valid for this module, but its full definition (with parameters) is in `sofistik.err`. The `=` syntax distinguishes references from full definitions.

## SOFISTIK Module (BASIC)

The `sofistik.err` file contains two types of commands:

1. **Generic commands** - Used by many modules (HEAD, PAGE, CTRL, NORM, etc.)
2. **Module-specific commands** - Full definitions for commands referenced elsewhere (SSLA, ARBL, etc.)

During extraction:
- Commands referenced in only ONE other module are moved to that module (e.g., SSLA → AQUA)
- Commands referenced in MULTIPLE modules stay in BASIC (e.g., PAGE, HEAD)
- The SOFISTIK module is renamed to BASIC in the output

## Extraction Notes

The `extract.py` script processes these files to generate JSON command definitions:

1. Commands are matched by `-10`/`-20`/`-*0` prefix + command name
2. Parameters are extracted with their type (enum/literal/keyword)
3. Enum parameters are tracked for later value assignment
4. Enum value lines assign values by parameter POSITION (not enum index)
5. German (`-10`) and English (`-20`) are paired; shared (`-*0`) applies to both
6. Empty reference commands are filled from SOFISTIK definitions
7. Single-module commands are removed from BASIC (moved to their target module)
8. Output is split into `sofistik.{version}.de.json` and `sofistik.{version}.en.json`
