import string
import os
import argparse
import glob
from itertools import product


# =========================
# Generator
# =========================

class CVCVGenerator:
    def __init__(
        self,
        vowels=None,
        consonants=None,
        add_vowels=None,
        add_consonants=None,
        include_y=False,
        first=None
    ):
        # -------------------------
        # Build VOWELS
        # -------------------------
        default_vowels = "aeiou"

        if include_y:
            default_vowels += "y"

        base_vowels = vowels if vowels else default_vowels

        if add_vowels:
            base_vowels += add_vowels

        # remove duplicates + normalize
        self.vowels = "".join(sorted(set(base_vowels.lower())))

        # -------------------------
        # Build CONSONANTS
        # -------------------------
        if consonants:
            base_consonants = consonants
        else:
            base_consonants = "".join(
                c for c in string.ascii_lowercase if c not in self.vowels
            )

        if add_consonants:
            base_consonants += add_consonants

        # remove duplicates + normalize
        self.consonants = "".join(sorted(set(base_consonants.lower())))

        self.first = first.lower() if first else None

    def generate(self):
        if self.first:
            if self.first not in self.consonants:
                raise ValueError(
                    f"First letter '{self.first}' must exist in consonant set."
                )
            first_letters = self.first
        else:
            first_letters = self.consonants

        for c1, v1, c2, v2 in product(
            first_letters,
            self.vowels,
            self.consonants,
            self.vowels
        ):
            yield c1 + v1 + c2 + v2
# =========================
# Filters
# =========================

class NameFilter:
    def apply(self, name: str) -> bool:
        return True


class NoFilter(NameFilter):
    pass


class OnlyRepeatingVowels(NameFilter):
    def apply(self, name):
        return name[1] == name[3]


class OnlyRepeatingConsonants(NameFilter):
    def apply(self, name):
        return name[0] == name[2]


class OnlyRepeatingBoth(NameFilter):
    def apply(self, name):
        return name[0] == name[2] and name[1] == name[3]


def get_filter(filter_type):
    filters = {
        "none": NoFilter(),
        "repeat_vowels": OnlyRepeatingVowels(),
        "repeat_consonants": OnlyRepeatingConsonants(),
        "repeat_both": OnlyRepeatingBoth(),
    }
    return filters.get(filter_type, NoFilter())


# =========================
# Engine
# =========================

class NameEngine:
    def __init__(self, generator, name_filter, suffix=""):
        self.generator = generator
        self.name_filter = name_filter
        self.suffix = suffix

    def run(self):
        for name in self.generator.generate():
            if self.name_filter.apply(name):
                yield name + self.suffix

    def export_grouped(self, folder="output"):
        os.makedirs(folder, exist_ok=True)

        grouped = {}

        for name in self.run():
            grouped.setdefault(name[0], []).append(name)

        # Determine which files SHOULD exist
        if self.generator.first:
            allowed_letters = {self.generator.first}
        else:
            allowed_letters = set(self.generator.consonants)

        # Delete unwanted txt files first
        for file_path in glob.glob(os.path.join(folder, "*.txt")):
            filename = os.path.basename(file_path)
            letter = filename.replace(".txt", "")
            if letter not in allowed_letters:
                os.remove(file_path)
                print(f"Deleted {file_path}")

        # Write allowed files (overwrite)
        for letter in allowed_letters:
            file_path = os.path.join(folder, f"{letter}.txt")
            names = grouped.get(letter, [])
            with open(file_path, "w") as f:
                f.write("\n".join(names))
            print(f"Wrote {file_path}")

        print(f"\nExport complete → {folder}/")


# =========================
# CLI
# =========================

def clear_output(folder="output", allowed_letters=None):
    if not os.path.exists(folder):
        print("No output folder exists.")
        return

    for file_path in glob.glob(os.path.join(folder, "*.txt")):
        filename = os.path.basename(file_path)
        name_without_ext = filename.replace(".txt", "")

        # Only target ONE-letter filenames
        if len(name_without_ext) == 1:
            if allowed_letters is None or name_without_ext not in allowed_letters:
                os.remove(file_path)
                print(f"Deleted {file_path}")

def main():
    parser = argparse.ArgumentParser(description="Advanced CVCV Name Generator")

    parser.add_argument(
        "--filter",
        choices=["none", "repeat_vowels", "repeat_consonants", "repeat_both"],
        default="none",
        help="Filter type"
    )

    parser.add_argument(
        "--suffix",
        type=str,
        default="",
        help="Optional suffix (e.g. ly, io, ai)"
    )

    parser.add_argument(
        "--vowels",
        type=str,
        help="Custom vowels (e.g. ae, io)"
    )

    parser.add_argument(
        "--consonants",
        type=str,
        help="Custom consonants (e.g. bcdkpr)"
    )

    parser.add_argument(
        "--first",
        type=str,
        help="Pin first character (must exist in consonant set)"
    )

    parser.add_argument(
        "--include-y",
        action="store_true",
        help="Include 'y' as vowel (if vowels not manually set)"
    )

    parser.add_argument(
        "--export",
        action="store_true",
        help="Export grouped files"
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear ALL output txt files"
    )
    
    parser.add_argument(
        "--add-vowels",
        type=str,
        help="Append additional vowels to base set"
    )

    parser.add_argument(
        "--add-consonants",
        type=str,
        help="Append additional consonants to base set"
    )

    args = parser.parse_args()

    output_folder = "output"
    
    allowed_letters = None

    if args.first:
        allowed_letters = {args.first}
    elif args.consonants:
        allowed_letters = set(args.consonants)

    # Clear mode
    if args.clear:
        clear_output(folder=output_folder, allowed_letters=allowed_letters)

    generator = CVCVGenerator(
        vowels=args.vowels,
        consonants=args.consonants,
        add_vowels=args.add_vowels,
        add_consonants=args.add_consonants,
        include_y=args.include_y,
        first=args.first
    )

    selected_filter = get_filter(args.filter)

    engine = NameEngine(
        generator=generator,
        name_filter=selected_filter,
        suffix=args.suffix
    )

    if args.export:
        engine.export_grouped(folder=output_folder)
    else:
        for name in engine.run():
            print(name)


if __name__ == "__main__":
    main()