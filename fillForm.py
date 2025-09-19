import json
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName, PdfObject
from pdfrw.objects.pdfstring import PdfString
from pdfrw.objects.pdfname import BasePdfName

# Load JSON answers
with open("Eating_Disorders_Answers.json", "r", encoding="utf-8") as f:
    answers = json.load(f)

# Load the PDF
pdf_path = "./public/Eating_Disorders.pdf"
pdf = PdfReader(pdf_path)

# Set NeedAppearances flag to help with rendering
if pdf.Root.AcroForm:
    pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject('true')))

def field_type(annotation):
    """Determine the type of form field"""
    ft = annotation.get('/FT')
    ff = annotation.get('/Ff')
    
    if ft == '/Tx':
        return 'text'
    if ft == '/Ch':
        if ff and int(ff) & (1 << 17):  # test 18th bit
            return 'combo'
        else:
            return 'list'
    if ft == '/Btn':
        if ff and int(ff) & (1 << 15):  # test 16th bit
            return 'radio'
        else:
            return 'checkbox'
    return 'unknown'

def radio_button(annotation, value):
    """Handle radio button selection"""
    if '/Kids' not in annotation:
        return False
        
    # Set each kid's appearance state
    for kid in annotation['/Kids']:
        # Get the export value for this kid
        keys = list(kid['/AP']['/N'].keys())
        keys.remove('/Off')
        export = keys[0] if keys else '/Off'
        
        if f'/{value}' == export:
            kid.update(PdfDict(AS=BasePdfName(f'/{value}')))
        else:
            kid.update(PdfDict(AS=BasePdfName('/Off')))
    
    # Set the parent's value
    annotation.update(PdfDict(V=BasePdfName(f'/{value}')))
    return True

def checkbox(annotation, value):
    """Handle checkbox selection"""
    # Get the export value
    keys = list(annotation['/AP']['/N'].keys())
    keys.remove('/Off')
    export = keys[0] if keys else '/Yes'
    
    if value:
        annotation.update(PdfDict(V=export, AS=export))
    else:
        # Delete V and AS fields for unchecked state
        if '/V' in annotation:
            del annotation['/V']
        if '/AS' in annotation:
            del annotation['/AS']

def text_form(annotation, value):
    """Handle text field"""
    pdfstr = PdfString.encode(str(value))
    annotation.update(PdfDict(V=pdfstr))

# Process all pages
for page in pdf.pages:
    annotations = page.get('/Annots')
    if annotations is None:
        continue

    for annotation in annotations:
        if annotation.get('/Subtype') != '/Widget':
            continue
        
        # Handle repeated fields (check for Parent)
        if not annotation.get('/T'):
            annotation = annotation.get('/Parent')
            if not annotation:
                continue
        
        field_name_obj = annotation.get('/T')
        if not field_name_obj:
            continue
            
        field_name = field_name_obj.to_unicode()
        value = answers.get(field_name)
        
        if value is None:
            print(f"⚠️ Skipping missing field: {field_name}")
            continue

        # Determine field type and handle accordingly
        ftype = field_type(annotation)
        
        if ftype == 'text':
            text_form(annotation, value)
            # Clear appearance to force regeneration
            if '/AP' in annotation:
                del annotation['/AP']
            print(f"✅ Text field '{field_name}' = '{value}'")
            
        elif ftype == 'checkbox':
            # Convert string values to boolean
            bool_value = str(value).lower() in ['true', 'yes', 'on', '1']
            checkbox(annotation, bool_value)
            print(f"✅ Checkbox '{field_name}' = {'checked' if bool_value else 'unchecked'}")
            
        elif ftype == 'radio':
            if radio_button(annotation, str(value)):
                print(f"✅ Radio group '{field_name}' = '{value}'")
            else:
                print(f"❌ Failed to set radio group '{field_name}' = '{value}'")
                
        elif ftype == 'combo':
            # Handle combo boxes if needed
            pdfstr = PdfString.encode(str(value))
            annotation.update(PdfDict(V=pdfstr, AS=pdfstr))
            print(f"✅ Combo field '{field_name}' = '{value}'")
            
        else:
            print(f"❓ Unknown field type '{ftype}' for '{field_name}'")

# Save the filled PDF
output_path = "filled_dbq.pdf"
PdfWriter().write(output_path, pdf)

print(f"✅ New filled PDF saved as {output_path}")