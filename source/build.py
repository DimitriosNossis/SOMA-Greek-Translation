"""Rebuild the Greek .lang files of the mod from the translation tables in this folder.

Usage (Python 3.8+, no extra packages):
    python build.py --soma "C:\\Program Files (x86)\\GOG Galaxy\\Games\\SOMA"

Reads from your SOMA install (nothing there is changed):
    config/lang_main/english.lang   the structure the story text is built on
    config/lang_main/french.lang    entry-name casing for the subtitle categories
Writes:
    ../mod/config/lang_main/greek.lang
    ../mod/config/base_greek.lang

Translation tables are UTF-8 text, one entry per line:  Category|EntryName<TAB>Greek text
    text/*.txt        story, terminals, notes (keys from english.lang)
    text/keep.txt     entries deliberately left as in English (names, codes)
    subtitles/*.txt   Voices_* subtitle categories
    menus/base_greek.xml  menus and options (readable form of base_greek.lang)
Inside the text: a pilcrow (U+00B6) stands for a line break inside an entry, U+21E5 for a tab,
and U+2205 for an intentionally empty entry.
"""
import argparse, collections, glob, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "..", "mod")
TOK = re.compile(r'<!--.*?-->|<CATEGORY Name="([^"]*)"|<Entry Name="([^"]*)">(.*?)</Entry>', re.S)
dec = lambda t: t.replace("\u00b6", "\r\n").replace("\u21e5", "\t")


def read(p):
    return open(p, encoding="utf-8", newline="").read()


def load_table(paths):
    tr = {}
    for p in paths:
        for ln in open(p, encoding="utf-8"):
            ln = ln.rstrip("\n")
            if not ln.strip() or ln.startswith("#") or "\t" not in ln:
                continue
            k, t = ln.split("\t", 1)
            if k in tr:
                raise SystemExit(f"duplicate key {k} in {p}")
            tr[k] = "" if t == "\u2205" else t
    return tr


def entries(raw):
    cat = None
    for m in TOK.finditer(raw):
        if m.group(1) is not None:
            cat = m.group(1)
        elif m.group(2) is not None:
            yield m, f"{cat}|{m.group(2)}"


def build_story(english_raw, tr):
    out, last, used = [], 0, set()
    for m, k in entries(english_raw):
        if k in tr:
            out += [english_raw[last:m.start(3)], dec(tr[k])]
            last = m.end(3)
            used.add(k)
    out.append(english_raw[last:])
    unknown = sorted(set(tr) - used)
    if unknown:
        print("warning: keys not found in english.lang:", unknown[:10])
    return "".join(out), len(used)


def build_voices(french_raw, tr):
    fr_case = collections.defaultdict(dict)
    cat = None
    for m in re.finditer(r'<CATEGORY Name="([^"]*)"|<Entry Name="([^"]*)">', french_raw):
        if m.group(1):
            cat = m.group(1)
        elif cat and cat.startswith("Voices_"):
            fr_case[cat][m.group(2).lower()] = m.group(2)
    cats = collections.OrderedDict()
    for k, t in tr.items():
        c, n = k.split("|", 1)
        cats.setdefault(c, []).append((fr_case.get(c, {}).get(n.lower(), n), t))
    out = []
    for c, items in cats.items():
        out.append(f'    <CATEGORY Name="{c}">\r\n')
        out += [f'        <Entry Name="{n}">{t}</Entry>\r\n' for n, t in items]
        out.append("    </CATEGORY>\r\n")
    return "".join(out), sum(len(v) for v in cats.values()), len(cats)


def escape(text):
    # SOMA's own translations store every non-ASCII character as [uNNNN]
    return "".join(ch if ord(ch) < 128 else f"[u{ord(ch)}]" for ch in text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--soma", default=r"C:\Program Files (x86)\GOG Galaxy\Games\SOMA", help="SOMA game folder")
    a = ap.parse_args()
    lang_main = os.path.join(a.soma, "config", "lang_main")
    english = read(os.path.join(lang_main, "english.lang"))
    french = read(os.path.join(lang_main, "french.lang"))

    text = load_table(sorted(glob.glob(os.path.join(HERE, "text", "tr_*.txt"))))
    story, n_text = build_story(english, text)
    voices, n_vo, n_cat = build_voices(french, load_table(sorted(glob.glob(os.path.join(HERE, "subtitles", "tr_*.txt")))))
    i = story.rindex("</LANGUAGE>")
    greek = story[:i] + voices + story[i:]
    with open(os.path.join(MOD, "config", "lang_main", "greek.lang"), "w", encoding="ascii", newline="") as f:
        f.write(escape(greek))

    menus = read(os.path.join(HERE, "menus", "base_greek.xml"))
    with open(os.path.join(MOD, "config", "base_greek.lang"), "w", encoding="ascii", newline="") as f:
        f.write(escape(menus))
    print(f"greek.lang: {n_text} text entries, {n_vo} subtitles in {n_cat} categories")
    print("base_greek.lang: written")


if __name__ == "__main__":
    main()
