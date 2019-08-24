#!/bin/python3
"""
Calculate used Flash and RAM in a given stm32 application.

Author: Sturla Lange
Date: 2019-08-24
Licence: MIT
"""
import sys
import argparse
import subprocess

parser = argparse.ArgumentParser(
    description="Calculate used Flash and RAM in a given stm32 application."
)
region_args_group = parser.add_argument_group("Max region size arguments")
used_size_group_mutex = parser.add_mutually_exclusive_group(required=True)

region_args_group.add_argument(
    "--linker_file",
    "-l",
    type=str,
    help="Path to a linker file to parse RAM and Flash size from.",
)
region_args_group.add_argument(
    "--max_flash_size",
    "-mf",
    type=str,
    help="The maximum Flash size. Can be hex, given in Kbytes e.g. (512K) or just a decimal. Overrides value parsed from linker file.",
)
region_args_group.add_argument(
    "--max_ram_size",
    "-mr",
    help="The maximum RAM size. Can be hex, given in Kbytes e.g. (512K) or just a decimal. Overrides value parsed from linker file.",
)

used_size_group_mutex.add_argument(
    "--file",
    "-f",
    type=str,
    help="Path to an elf file to be passed to arm-none-eabi-size.",
)
used_size_group_mutex.add_argument(
    "--stdin",
    "-s",
    action="store_true",
    help="Accept arm-none-eabi-size data from stdin (think pipe).",
)

args = parser.parse_args()


def parse_linker_file(s, substr):
    substr_pos = s.find(substr + " (")
    if substr_pos != -1:
        return parse_input(
            s[s.find("=", s.find("\n", substr_pos) - 6) + 2 : s.find("\n", substr_pos)]
        )
    else:
        return -1


def pct_region(size, max_size):
    return 100 * size / max_size


def parse_input(x):
    if x[-1] == "K":
        return int(x[:-1]) * 1024
    else:
        return int(x, 0)


def parse_regions(raw):
    return [int(x.strip()) for x in raw.splitlines()[1].split("\t")[:3]]


def print_region(name, size, max_size):
    print(f"{name} used: {size} / {max_size} ({pct_region(size, max_size):.1f}%)")


def call_size(f):
    return subprocess.check_output(
        [f"arm-none-eabi-size {f}"], shell=True, encoding="utf8"
    )


if __name__ == "__main__":
    # Get the region size from arguments or linker file
    max_flash = 0
    max_ram = 0
    if args.linker_file:
        with open(args.linker_file) as f:
            s = f.read()
            max_flash = parse_linker_file(s, "FLASH")
            max_ram = parse_linker_file(s, "RAM")
            if max_flash < 0 or max_ram < 0:
                parser.exit(1, "RAM and FLASH section not found in linker file\n")
    if args.max_flash_size:
        max_flash = parse_input(args.max_flash_size)
    if args.max_ram_size:
        max_ram = parse_input(args.max_ram_size)
    if not (max_flash or max_ram):
        parser.exit(
            1,
            "Supply max flash and RAM size with -mf and -mr respectively or the linker file with -l\n",
        )

    # Get the used size from stdin or by calling size on an elf file
    if args.file:
        raw = call_size(args.file)
    elif args.stdin:
        raw = sys.stdin.read()
    else:
        parser.exit(
            1, "Supply the data on stdin and with -s or point to an elf file with -f\n"
        )

    text, data, bss = parse_regions(raw)

    # Calculate actual size used
    flash = text + data
    ram = data + bss

    if max_flash:
        print_region("Flash", flash, max_flash)
    if max_ram:
        print_region("  RAM", ram, max_ram)
