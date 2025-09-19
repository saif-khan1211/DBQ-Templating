import os
import json
from pdfrw import PdfReader
from dbq.fillForm import fillForm

def main():
    base = os.path.dirname(__file__)
    json_dir = os.path.join(base, 'json_data')
    pdf_dir = os.path.join(base, 'dbq_files')
    os.makedirs(json_dir, exist_ok=True)

    # If no JSON exists, generate a minimal placeholder from field names
    json_path = os.path.join(json_dir, 'ALS_DBQ_sample_answers.json')
    if not os.path.exists(json_path):
        pdf_path = os.path.join(pdf_dir, 'ALS_Lou_Gehrigs_Disease.pdf')
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f'Missing PDF at {pdf_path}')
        pdf = PdfReader(pdf_path)
        names = set()
        for page in pdf.pages:
            for a in getattr(page, 'Annots', []) or []:
                try:
                    t = a.get('/T')
                    if not t:
                        continue
                    name = t.to_unicode() if hasattr(t, 'to_unicode') else str(t)
                    names.add(name)
                except Exception:
                    continue
        minimal = {n: "" for n in sorted(names)}
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(minimal, f, indent=2)

    fillForm()

if __name__ == "__main__":
    main()