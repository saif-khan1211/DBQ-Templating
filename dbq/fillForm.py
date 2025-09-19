import os
import json
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName, PdfObject


def fillForm():
    # Base paths (project root)
    base_dir = os.path.dirname(os.path.dirname(__file__))
    json_dir = os.path.join(base_dir, "json_data")
    pdf_dir = os.path.join(base_dir, "dbq_files")
    out_dir = os.path.join(base_dir, "dbq_files_generated")
    os.makedirs(out_dir, exist_ok=True)

    # Inputs
    json_path = os.path.join(json_dir, "ALS_DBQ_sample_answers.json")
    pdf_path = os.path.join(pdf_dir, "ALS_Lou_Gehrigs_Disease.pdf")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Answers JSON not found: {json_path}")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        answers = json.load(f)

    pdf = PdfReader(pdf_path)

    # Encourage viewers to regenerate appearances
    try:
        if getattr(pdf.Root, 'AcroForm', None):
            pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject('true')))
        else:
            pdf.Root.AcroForm = PdfDict(NeedAppearances=PdfObject('true'))
    except Exception:
        pass

    # First pass: fill text/choice; collect button widgets by group name
    btn_groups = {}
    for page in pdf.pages:
        if '/Annots' not in page:
            continue
        for annot in page.Annots:
            if annot.Subtype != PdfName('Widget'):
                continue

            field = annot.get('/T')
            parent = annot.get('/Parent')
            name = None
            if field:
                try:
                    name = field.to_unicode()
                except Exception:
                    name = str(field)
            elif parent and parent.get('/T'):
                try:
                    name = parent.get('/T').to_unicode()
                except Exception:
                    name = str(parent.get('/T'))
            if not name:
                continue

            ftype = annot.get('/FT')
            if ftype == PdfName('Btn'):
                # Group by the logical field name (parent or widget name)
                btn_groups.setdefault(name, []).append(annot)
                continue

            value = answers.get(name)
            if value is None:
                continue

            if ftype == PdfName('Tx'):
                annot.update(PdfDict(V=str(value)))
            elif ftype == PdfName('Ch'):
                annot.update(PdfDict(V=str(value), AS=str(value)))

    # Optional per-group index overrides
    overrides = {}
    try:
        ov_path = os.path.join(json_dir, 'button_overrides.json')
        if os.path.exists(ov_path):
            with open(ov_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    overrides = loaded
    except Exception:
        overrides = {}

    # Second pass: resolve radio/checkbox groups (supports Yes/No and explicit index)
    def get_on_state(a):
        ap = a.get('/AP')
        try:
            if ap and ap.get('N'):
                keys = [str(k)[1:] if str(k).startswith('/') else str(k) for k in ap.N.keys()]
                for k in keys:
                    if k and k != 'Off':
                        return k
        except Exception:
            pass
        # fallbacks
        return 'Yes'

    for group_name, widgets in btn_groups.items():
        desired = answers.get(group_name)
        if desired is None:
            continue
        val_str = str(desired).strip()
        val_norm = val_str.lower()

        # 1) If JSON provides an explicit index (int or numeric string), use it
        explicit_index = None
        if isinstance(desired, int):
            explicit_index = desired
        else:
            if val_str.isdigit():
                try:
                    explicit_index = int(val_str)
                except Exception:
                    explicit_index = None

        is_truthy = val_norm in ['true', 'yes', 'on', '1', 'y']

        parent_obj = None
        if widgets:
            parent_obj = widgets[0].get('/Parent') if widgets[0] is not None else None

        if len(widgets) == 1:
            # Single checkbox semantics
            a = widgets[0]
            on_name = get_on_state(a)
            try:
                if is_truthy:
                    a.update(PdfDict(V=PdfName(on_name), AS=PdfName(on_name)))
                else:
                    a.update(PdfDict(V=PdfName('Off'), AS=PdfName('Off')))
            except Exception:
                pass
            continue

        # Radio group selection
        if explicit_index is not None:
            selected_index = max(0, min(len(widgets) - 1, explicit_index))
        else:
            # Use per-group overrides if present. Default assumption: index 0 = No, index 1 = Yes
            ov = overrides.get(group_name, {}) if isinstance(overrides, dict) else {}
            truthy_idx = ov.get('truthy_index', 1 if len(widgets) > 1 else 0)
            falsy_idx = ov.get('falsy_index', 0)
            selected_index = truthy_idx if is_truthy else falsy_idx
            selected_index = max(0, min(len(widgets) - 1, selected_index))
        for i, a in enumerate(widgets):
            on_name = get_on_state(a)
            try:
                if i == selected_index:
                    # Set group value and widget appearance
                    if parent_obj:
                        parent_obj.update(PdfDict(V=PdfName(on_name)))
                    a.update(PdfDict(AS=PdfName(on_name)))
                else:
                    a.update(PdfDict(AS=PdfName('Off')))
            except Exception:
                pass

    # Output
    out_path = os.path.join(out_dir, "filled_ALS_Lou_Gehrigs_Disease.pdf")
    PdfWriter().write(out_path, pdf)
    print(f"✅ New filled PDF saved as {out_path} (not flattened)")


if __name__ == "__main__":
    fillForm()
