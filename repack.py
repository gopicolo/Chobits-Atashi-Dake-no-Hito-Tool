# repack_final_v9.py
import struct
import os
import re

# --- CONFIGURATION ---
rom_filename = "Chobits - Atashi Dake no Hito (Japan).gba"
translated_text_filename = "dialogue_for_translation.txt"
new_rom_filename = "chobits_translated.gba"

# --- OFFSETS ---
table_start_offset = 0x84E74
free_space_start_offset = 0x732254

# --- GAME-SPECIFIC BYTES ---
terminator = b'\x00'
newline_char = b'\x0a'
player_name_full_code = b'\x02\x01'
player_name_first_code = b'\x01'
player_name_last_code = b'\x02'

# --- TAGS ---
TAG_MAP = {
    '[PLAYER_NAME]': player_name_full_code,
    '[PLAYER_NAME_FIRST]': player_name_first_code,
    '[PLAYER_NAME_LAST]': player_name_last_code
}

# --- REGEX PATTERNS ---
hex_tag_pattern = r"<\$\s*([0-9A-F\s]+)\s*\$>"
named_tag_pattern = '|'.join(re.escape(k) for k in TAG_MAP.keys())
generic_byte_tag_pattern = r"<([0-9A-F]{2})>"
combined_pattern = re.compile(f"({hex_tag_pattern}|{named_tag_pattern}|{generic_byte_tag_pattern})")

# ---------------------------------

def parse_text_file(filename):
    print(f"Reading and parsing '{filename}'...")
    entries = {}
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = re.compile(
        r"<STRING (\d+?)>\nPOINTER_OFFSET: 0x([0-9A-F]+)\n(?:TEXT_OFFSET: 0x[0-9A-F]+\n)?([\s\S]*?)\n\n",
        re.MULTILINE
    )
    for match in pattern.finditer(content):
        pointer_offset = int(match.group(2), 16)
        text = match.group(3)
        if "(Null or Invalid Pointer:" not in text:
            entries[pointer_offset] = text
    print(f"Found {len(entries)} translatable text entries.")
    return entries

# --- CLEAN TEXT (OPTIONAL) ---
def clean_text_for_shiftjis(s):
    replacements = {
        '♪': '',    # remove nota musical
        '€': 'E',   # euro
        # adicione outros conforme necessário
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s

# --- ENCODE TEXT WITH TAGS ---
def encode_text_with_tags(text, pointer_offset=None):
    text = text.replace('\n', chr(newline_char[0]))
    text = clean_text_for_shiftjis(text)

    def replacer(match):
        tag = match.group(0)
        if tag in TAG_MAP:
            return TAG_MAP[tag].decode('latin1')  # bytes temporários
        elif tag.startswith('<$') and tag.endswith('$>'):
            hex_string = tag[2:-2].strip().replace(" ", "")
            return bytes.fromhex(hex_string).decode('latin1')
        elif re.fullmatch(r"<([0-9A-F]{2})>", tag):
            return bytes([int(tag[1:-1], 16)]).decode('latin1')
        else:
            return tag

    # substitui todas as tags por bytes temporários
    processed_text = combined_pattern.sub(replacer, text)

    # codifica em Shift-JIS somente o texto normal
    try:
        encoded_bytes = processed_text.encode('shift_jis')
    except UnicodeEncodeError as e:
        char = processed_text[e.start:e.end]
        print(f"\n[ERROR] Cannot encode character '{char}' in pointer offset {hex(pointer_offset)}")
        print(f"Position in string: {e.start}-{e.end}")
        print(f"Full text: {text}\n")
        raise e
    return encoded_bytes

# --- MAIN ---
if not all(os.path.exists(f) for f in [rom_filename, translated_text_filename]):
    print("ERROR: One or more required files (ROM or text file) are missing.")
else:
    print("Reading original ROM into memory...")
    with open(rom_filename, 'rb') as f:
        rom_data = bytearray(f.read())

    translated_entries = parse_text_file(translated_text_filename)

    print(f"\nWriting new text into free space starting at {hex(free_space_start_offset)}...")
    current_text_offset = free_space_start_offset
    new_pointers = {}

    for pointer_offset, text_string in translated_entries.items():
        new_pointers[pointer_offset] = current_text_offset
        encoded_text = encode_text_with_tags(text_string, pointer_offset)

        # grava no ROM
        rom_data[current_text_offset:current_text_offset+len(encoded_text)] = encoded_text
        current_text_offset += len(encoded_text)
        rom_data[current_text_offset] = terminator[0]
        current_text_offset += 1

    print(f"Finished writing new text. Last byte written at {hex(current_text_offset)}.")
    if current_text_offset > 0x7FFFFF:
        print("\n!!! WARNING: New text is too large and has overwritten the end of the ROM file!")

    # --- UPDATE POINTERS ---
    print("\nUpdating pointer table...")
    for original_pointer_offset, new_text_location in new_pointers.items():
        new_pointer_value = 0x08000000 + new_text_location
        new_pointer_bytes = struct.pack('<I', new_pointer_value)
        rom_data[original_pointer_offset:original_pointer_offset+4] = new_pointer_bytes

    print(f"Writing all changes to new ROM file: '{new_rom_filename}'...")
    with open(new_rom_filename, 'wb') as f:
        f.write(rom_data)

    print("\nRepack finished successfully! 🎉")
