import os
import json
from pdfrw import PdfReader, PdfName


def to_str(obj):
    if obj is None:
        return None
    try:
        if hasattr(obj, 'to_unicode'):
            return obj.to_unicode()
    except Exception:
        pass
    s = str(obj)
    if s.startswith('/'):
        return s[1:]
    return s


def main():
    base = os.path.dirname(__file__)
    filled_path = os.path.join(base, 'dbq_files_generated', 'filled_ALS_Lou_Gehrigs_Disease.pdf')
    json_path = os.path.join(base, 'json_data', 'ALS_DBQ_sample_answers.json')
    if not os.path.exists(filled_path):
        print('Filled PDF not found:', filled_path)
        return 2
    if not os.path.exists(json_path):
        print('JSON not found:', json_path)
        return 2

    with open(json_path, 'r', encoding='utf-8') as f:
        answers = json.load(f)

    pdf = PdfReader(filled_path)

    groups = {}
    for pnum, page in enumerate(pdf.pages, start=1):
        for annot in getattr(page, 'Annots', []) or []:
            try:
                if annot.Subtype != PdfName('Widget'):
                    continue
                field = annot.get('/T')
                parent = annot.get('/Parent')
                name = None
                if field:
                    name = to_str(field)
                elif parent and parent.get('/T'):
                    name = to_str(parent.get('/T'))
                if not name:
                    continue
                if annot.get('/FT') != PdfName('Btn'):
                    continue
                groups.setdefault(name, []).append(annot)
            except Exception:
                continue

    total = 0
    issues = 0
    for name, annots in groups.items():
        expected = answers.get(name)
        if expected is None:
            continue
        total += 1
        states = [to_str(a.get('/AS')) for a in annots]
        selected_indexes = [i for i, s in enumerate(states) if s and s != 'Off']
        exp_norm = str(expected).strip().lower()
        exp_truthy = exp_norm in ['yes', 'true', 'on', '1', 'y']
        exp_index = None
        if str(expected).isdigit():
            try:
                exp_index = int(str(expected))
            except Exception:
                exp_index = None
        # Determine if matches our intended mapping
        if len(annots) == 1:
            # Checkbox semantics: truthy => selected any; falsy => none selected
            ok = (bool(selected_indexes) == exp_truthy)
        else:
            # Radio semantics (default mapping: index 0 = No, index 1 = Yes)
            should_index = exp_index
            if should_index is None:
                should_index = 1 if exp_truthy else 0
            ok = (selected_indexes == [should_index])
        if not ok:
            issues += 1
            print(f"Mismatch: {name}")
            if len(annots) == 1:
                print("  expected:", expected, "(truthy:", exp_truthy, ")")
                print("  selected:", bool(selected_indexes), " raw state:", states[0])
            else:
                print("  expected:", expected, "(index:", should_index, ")")
                print("  selected indexes:", selected_indexes, " raw states:", states)

    print(f"Checked groups: {total}")
    print(f"Groups with mismatches: {issues}")
    return 0 if issues == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())


