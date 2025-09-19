from pdfrw import PdfReader

def extract_fields(obj, fields, parent_name=""):
    """
    Recursively extract all field names, including nested /Kids.
    """
    if not obj:
        return

    if isinstance(obj, list):
        for o in obj:
            extract_fields(o, fields, parent_name)
    elif isinstance(obj, dict):
        # Field name
        t = obj.get('/T')
        name = t.to_unicode() if hasattr(t, 'to_unicode') else str(t) if t else None
        if parent_name and name:
            full_name = f"{parent_name}.{name}"
        else:
            full_name = name or parent_name
        if full_name:
            fields.add(full_name)

        # Recurse into /Kids
        kids = obj.get('/Kids')
        if kids:
            extract_fields(kids, fields, full_name)

        # Recurse into /Annots
        annots = obj.get('/Annots')
        if annots:
            extract_fields(annots, fields, parent_name)

def main():
    pdf_path = "./public/Eating_Disorders.pdf"
    pdf = PdfReader(pdf_path)

    all_fields = set()

    # Extract from AcroForm top-level fields
    acroform = getattr(pdf.Root, 'AcroForm', None)
    if acroform:
        extract_fields(getattr(acroform, 'Fields', []), all_fields)

    # Extract from page annotations
    for page in pdf.pages:
        extract_fields(getattr(page, 'Annots', []), all_fields)

    # Print sorted field names
    for name in sorted(all_fields):
        print(name)


if __name__ == "__main__":
    main()
