# repack_final_v2.py
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
player_name_code = b'\x02\x01'

# This dictionary maps our text tags back to their original bytes
TAG_MAP = {
    '[PLAYER_NAME]': player_name_code
    # Add other named tags here if you find more, e.g., '[HEART]': b'\xF0\xD6'
}

# ---------------------------------

def parse_text_file(filename):
    """Reads the formatted text file and parses it into a dictionary."""
    print(f"Reading and parsing '{filename}'...")
    entries = {}
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = re.compile(r"<STRING (\d+?)>\nPOINTER_OFFSET: 0x([0-9A-F]+)\n(?:TEXT_OFFSET: 0x[0-9A-F]+\n)?([\s\S]*?)\n\n", re.MULTILINE)
    for match in pattern.finditer(content):
        pointer_offset = int(match.group(2), 16)
        text = match.group(3)
        if "(Null or Invalid Pointer:" not in text:
            entries[pointer_offset] = text
    print(f"Found {len(entries)} translatable text entries.")
    return entries

# --- MAIN SCRIPT ---
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

    # Create a regex that finds BOTH our custom hex tags AND our named tags
    hex_tag_pattern = r"<\$\s*([0-9A-F\s]+)\s*\$>"
    named_tag_pattern = '|'.join(re.escape(k) for k in TAG_MAP.keys())
    combined_pattern = re.compile(f"({hex_tag_pattern}|{named_tag_pattern})")

    for pointer_offset, text_string in translated_entries.items():
        new_pointers[pointer_offset] = current_text_offset
        
        # Replace text newlines with the game's newline byte
        processed_text = text_string.replace('\n', chr(newline_char[0]))

        parts = combined_pattern.split(processed_text)
        
        for part in parts:
            if not part: continue # Skip empty strings from the split

            if part in TAG_MAP:
                # If this part is a named tag (like [PLAYER_NAME]), write its bytes
                encoded_bytes = TAG_MAP[part]
            elif part.startswith('<$') and part.endswith('$>'):
                 # If this part is a hex tag, convert it back to bytes
                hex_string = part[2:-2].strip().replace(" ", "")
                encoded_bytes = bytes.fromhex(hex_string)
            else:
                # Otherwise, encode it as Shift-JIS
                try:
                    encoded_bytes = part.encode('shift_jis')
                except Exception as e:
                    print(f"ERROR encoding part '{part}' for pointer {hex(pointer_offset)}: {e}")
                    encoded_bytes = b''
            
            rom_data[current_text_offset : current_text_offset + len(encoded_bytes)] = encoded_bytes
            current_text_offset += len(encoded_bytes)
        
        rom_data[current_text_offset] = terminator[0]
        current_text_offset += 1

    print(f"Finished writing new text. Last byte written at {hex(current_text_offset)}.")
    if current_text_offset > 0x7FFFFF:
        print("\n!!! WARNING: New text is too large and has overwritten the end of the ROM file!")

    print("\nUpdating pointer table...")
    for original_pointer_offset, new_text_location in new_pointers.items():
        new_pointer_value = 0x08000000 + new_text_location
        new_pointer_bytes = struct.pack('<I', new_pointer_value)
        rom_data[original_pointer_offset : original_pointer_offset + 4] = new_pointer_bytes

    print(f"Writing all changes to new ROM file: '{new_rom_filename}'...")
    with open(new_rom_filename, 'wb') as f:
        f.write(rom_data)

    print("\nRepack finished successfully! 🎉")