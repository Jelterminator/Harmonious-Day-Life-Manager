# detect_non_utf8.py
import sys

def find_non_utf8(file_path):
    print(f"Scanning file: {file_path}\n")
    with open(file_path, "rb") as f:
        for lineno, line in enumerate(f, start=1):
            for i, byte in enumerate(line):
                try:
                    bytes([byte]).decode("utf-8")
                except UnicodeDecodeError:
                    print(f"Line {lineno}, Byte {i}: Non-UTF-8 byte {byte}")
                    print(f"    Line content: {line.decode('utf-8', errors='replace').rstrip()}")
                    break  # Move to next line after first invalid byte

if __name__ == "__main__":
    find_non_utf8("C:/Users/jelte/OneDrive/Desktop/Harmonious-Day-Life-Manager/main.py")
