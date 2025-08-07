# 🛠️ Chobits GBA Translation Tool

Custom romhacking tools created by **gopicolo** for extracting
and reinserting dialogue from the Game Boy Advance game:  
**Chobits - Atashi Dake no Hito (Japan)**.

This project includes two main scripts:
- `dump.py`: Extracts all translatable dialogue from the ROM.
- `repack.py`: Reinserts translated text into the ROM and updates the pointer table accordingly.

---

## 📂 Files

### `dump.py`
Reads the original ROM and creates a formatted text file ready for translation.

**Output:** `dialogue_for_translation.txt`

Each block includes:
- String ID
- Pointer offset
- Text offset (when valid)
- Decoded Shift-JIS text with special codes marked

Special codes like the player name are marked as `[PLAYER_NAME]`, and unknown bytes are shown as `<$ HEX $>`.

---

### `repack.py`
Reads the translated text file and reinserts all strings into free space in the ROM:
- Re-encodes all text in Shift-JIS
- Converts tags like `[PLAYER_NAME]` and `<$ XX $>` back into bytes
- Updates the original pointers
- Writes a new ROM file with the translated text

**Output:** `chobits_translated.gba`

The script also checks if the new text overflows the ROM and warns if needed.

---

## 🔧 Configuration

All file names, offsets, and control bytes are preconfigured specifically for:
**Chobits - Atashi Dake no Hito (Japan).gba**

No additional setup is required.

---

## 💬 Text Tagging

Control codes and special bytes use a readable tagging system:
- `[PLAYER_NAME]` → Replaced with `\x02\x01`
- `<$ XX $>` → Inserts raw byte(s), e.g. `<$ 0A $>` = `\x0A`

Text is encoded and decoded using **Shift-JIS**.

---

## ✅ Requirements

- Python 3.x
- No external libraries required
