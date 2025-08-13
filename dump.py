# dumper_final_v4.py
import struct
import os
import codecs

# --- CONFIGURATION ---
rom_filename = "Chobits - Atashi Dake no Hito (Japan).gba"
table_start_offset = 0x84E74
table_end_offset = 0x8DCC8
output_filename = "dialogue_for_translation.txt"

# --- GAME-SPECIFIC BYTES ---
terminator = b'\x00'
newline_char = b'\x0a'
player_name_full_code = b'\x02\x01'   # nome completo
player_name_first_code = b'\x01'      # primeiro nome
player_name_last_code = b'\x02'       # sobrenome

# ---------------------------------

def custom_sjis_error_handler(e):
    if not isinstance(e, UnicodeDecodeError):
        raise e
    bad_bytes = e.object[e.start:e.end]
    hex_representation = bad_bytes.hex().upper()
    replacement_text = f"<$ {hex_representation} $>"
    return (replacement_text, e.end)

codecs.register_error("custom_sjis", custom_sjis_error_handler)

def read_string_from(data, offset, terminator_byte):
    end_index = data.find(terminator_byte, offset)
    if end_index == -1:
        end_index = len(data)
    chunk = data[offset:end_index]

    result = []
    i = 0
    while i < len(chunk):
        # PLAYER_NAME_FULL
        if chunk[i:i+2] == player_name_full_code:
            result.append("[PLAYER_NAME]")
            i += 2
            continue
        # PLAYER_NAME_FIRST
        if chunk[i:i+1] == player_name_first_code:
            result.append("[PLAYER_NAME_FIRST]")
            i += 1
            continue
        # PLAYER_NAME_LAST
        if chunk[i:i+1] == player_name_last_code:
            result.append("[PLAYER_NAME_LAST]")
            i += 1
            continue

        b = chunk[i]

        # Newline
        if b == newline_char[0]:
            result.append("\n")
            i += 1
            continue

        # Control bytes <XX>
        if b < 0x20:
            result.append(f"<{b:02X}>")
            i += 1
            continue

        # Shift-JIS normal
        try:
            char = bytes([b]).decode("shift_jis")
            result.append(char)
            i += 1
        except UnicodeDecodeError:
            if i+1 < len(chunk):
                try:
                    char = chunk[i:i+2].decode("shift_jis")
                    result.append(char)
                    i += 2
                    continue
                except UnicodeDecodeError:
                    result.append(f"<$ {chunk[i]:02X} $>")
                    i += 1
            else:
                result.append(f"<$ {chunk[i]:02X} $>")
                i += 1

    return "".join(result)

# --- MAIN ---
if not os.path.exists(rom_filename):
    print(f"ERROR: ROM file '{rom_filename}' not found.")
else:
    print(f"Reading ROM '{rom_filename}' into memory...")
    with open(rom_filename, 'rb') as f:
        rom_data = f.read()
    print("ROM read complete.")

    table_data = rom_data[table_start_offset:table_end_offset]
    pointer_count = len(table_data) // 4

    print(f"Table found with {pointer_count} pointers.")
    print(f"Extracting text to '{output_filename}'...")

    with open(output_filename, 'w', encoding='utf-8') as output_file:
        for i in range(pointer_count):
            start = i * 4
            end = start + 4
            pointer_bytes = table_data[start:end]

            if len(pointer_bytes) < 4:
                continue

            address = struct.unpack('<I', pointer_bytes)[0]
            pointer_offset = table_start_offset + start

            if 0x08000000 < address < 0x09000000:
                file_offset = address - 0x08000000
                text_string = read_string_from(rom_data, file_offset, terminator)
                output_block = f"""<STRING {i:04}>
POINTER_OFFSET: 0x{pointer_offset:08X}
TEXT_OFFSET: 0x{file_offset:08X}
{text_string}

"""
            else:
                output_block = f"""<STRING {i:04}>
POINTER_OFFSET: 0x{pointer_offset:08X}
(Null or Invalid Pointer: 0x{address:X})

"""
            output_file.write(output_block)

    print(f"\nExtraction complete! Check '{output_filename}'.")
