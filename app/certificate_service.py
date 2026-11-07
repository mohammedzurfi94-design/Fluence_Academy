"""
Fluence English Academy - Official PDF Certificate Generator
Generates high-resolution, vector PDF certificates for students who complete the placement test.
100% Pure Python (Zero external dependencies).
"""

import os
from datetime import datetime

def sanitize_pdf_text(text: str) -> str:
    """Escapes parenthesis and normalizes non-ASCII characters for standard PDF Type 1 fonts."""
    if not text:
        return "Student"
    res = []
    for c in str(text):
        if ord(c) < 128:
            if c in '()\\':
                res.append('\\' + c)
            else:
                res.append(c)
        else:
            res.append(' ')
    cleaned = ''.join(res).strip()
    return cleaned or "Fluence Academy Student"

def create_certificate_pdf(
    student_name: str,
    score: int,
    total_questions: int,
    level: str,
    cert_id: str,
    issue_date: str,
    output_path: str
) -> str:
    """
    Creates an official, landscape A4 PDF Certificate of English Proficiency.
    Returns the absolute path to the generated PDF.
    """
    percentage = round((score / total_questions) * 100, 1) if total_questions > 0 else 0

    clean_name = sanitize_pdf_text(student_name)
    clean_level = sanitize_pdf_text(level).upper()
    clean_id = sanitize_pdf_text(cert_id)
    clean_date = sanitize_pdf_text(issue_date)

    desc_map = {
        'A1': 'Beginner - Foundational Language User',
        'A2': 'Elementary - Basic Practical User',
        'B1': 'Intermediate - Independent Everyday & Academic User',
        'B2': 'Upper-Intermediate - Operational Professional & Academic Competence',
        'C1': 'Advanced - Effective Academic Fluency & Complex Discourse',
        'C2': 'Mastery - Native-like Accuracy & Scholarly Precision'
    }
    level_short = clean_level.split()[0] if clean_level else 'B1'
    standing = desc_map.get(level_short, 'Independent Language User')

    stream_ops = []

    # 1. Background Fill
    stream_ops.append('1 1 1 rg 0 0 842 595 re f')

    # 2. Outer Border (Royal Navy)
    stream_ops.append('0.06 0.13 0.28 RG 6 w 25 25 792 545 re S')

    # 3. Inner Border (Rich Gold)
    stream_ops.append('0.82 0.68 0.21 RG 2 w 33 33 776 529 re S')

    # 4. Thin Border (Royal Navy)
    stream_ops.append('0.06 0.13 0.28 RG 0.75 w 38 38 766 519 re S')

    # 5. Corner Accents
    stream_ops.append('0.82 0.68 0.21 rg')
    stream_ops.append('33 33 12 12 re f')
    stream_ops.append('797 33 12 12 re f')
    stream_ops.append('33 550 12 12 re f')
    stream_ops.append('797 550 12 12 re f')

    # 6. Header: Academy Name
    academy_title = 'FLUENCE ENGLISH ACADEMY'
    w_title = len(academy_title) * 14.2
    x_title = 421 - (w_title / 2)
    stream_ops.append(f'BT /F2 24 Tf 0.06 0.13 0.28 rg {x_title:.1f} 518 Td ({academy_title}) Tj ET')

    sub_title = 'AN ACCREDITED ACADEMIC & RESEARCH LANGUAGE INSTITUTION'
    w_sub = len(sub_title) * 5.8
    x_sub = 421 - (w_sub / 2)
    stream_ops.append(f'BT /F1 9.5 Tf 0.35 0.38 0.44 rg {x_sub:.1f} 502 Td ({sub_title}) Tj ET')

    # Gold separator line
    stream_ops.append('0.82 0.68 0.21 RG 1.5 w 260 492 m 582 492 l S')

    # 7. Certificate Title
    cert_title = 'CERTIFICATE OF ENGLISH PROFICIENCY'
    w_ct = len(cert_title) * 14.5
    x_ct = 421 - (w_ct / 2)
    stream_ops.append(f'BT /F3 24 Tf 0.78 0.62 0.18 rg {x_ct:.1f} 456 Td ({cert_title}) Tj ET')

    assessment_sub = 'Diagnostic Assessment of Language & Academic Competence'
    w_as = len(assessment_sub) * 6.0
    x_as = 421 - (w_as / 2)
    stream_ops.append(f'BT /F1 10.5 Tf 0.28 0.30 0.35 rg {x_as:.1f} 438 Td ({assessment_sub}) Tj ET')

    # 8. Conferred To
    certify_text = 'This is to officially certify that'
    w_certify = len(certify_text) * 6.5
    x_certify = 421 - (w_certify / 2)
    stream_ops.append(f'BT /F4 13 Tf 0.30 0.32 0.38 rg {x_certify:.1f} 405 Td ({certify_text}) Tj ET')

    # 9. Student Name
    w_name = len(clean_name) * 12.5
    x_name = 421 - (w_name / 2)
    stream_ops.append(f'BT /F2 22 Tf 0.06 0.13 0.28 rg {x_name:.1f} 374 Td ({clean_name}) Tj ET')
    stream_ops.append(f'0.82 0.68 0.21 RG 1 w {max(180, x_name - 20):.1f} 366 m {min(662, x_name + w_name + 20):.1f} 366 l S')

    # 10. Test Description
    line1 = 'has successfully completed the comprehensive 20-question diagnostic placement test,'
    w_l1 = len(line1) * 5.6
    x_l1 = 421 - (w_l1 / 2)
    stream_ops.append(f'BT /F1 10 Tf 0.25 0.27 0.32 rg {x_l1:.1f} 344 Td ({line1}) Tj ET')

    line2 = 'demonstrating rigorous language proficiency and academic performance as evaluated below:'
    w_l2 = len(line2) * 5.6
    x_l2 = 421 - (w_l2 / 2)
    stream_ops.append(f'BT /F1 10 Tf 0.25 0.27 0.32 rg {x_l2:.1f} 330 Td ({line2}) Tj ET')

    # 11. Results Card Box
    stream_ops.append('0.96 0.97 0.99 rg 0.82 0.68 0.21 RG 1.2 w 161 236 520 76 re B')

    badge_text = f'CEFR LEVEL ASSIGNED:  LEVEL {clean_level}'
    w_badge = len(badge_text) * 9.2
    x_badge = 421 - (w_badge / 2)
    stream_ops.append(f'BT /F2 15 Tf 0.06 0.13 0.28 rg {x_badge:.1f} 286 Td ({badge_text}) Tj ET')

    score_text = f'Assessment Score: {score} / {total_questions} ({percentage}%)   |   Status: Verified Examination'
    w_score = len(score_text) * 6.3
    x_score = 421 - (w_score / 2)
    stream_ops.append(f'BT /F1 11 Tf 0.18 0.20 0.25 rg {x_score:.1f} 266 Td ({score_text}) Tj ET')

    standing_text = f'Proficiency Standing: {standing}'
    w_st = len(standing_text) * 5.2
    x_st = 421 - (w_st / 2)
    stream_ops.append(f'BT /F4 9.5 Tf 0.40 0.45 0.52 rg {x_st:.1f} 248 Td ({standing_text}) Tj ET')

    # 12. Bottom Left: Verification Details
    stream_ops.append('BT /F2 9.5 Tf 0.15 0.18 0.24 rg 70 148 Td (Verification Details:) Tj ET')
    stream_ops.append(f'BT /F1 9 Tf 0.30 0.35 0.42 rg 70 133 Td (Certificate ID: {clean_id}) Tj ET')
    stream_ops.append(f'BT /F1 9 Tf 0.30 0.35 0.42 rg 70 119 Td (Issue Date: {clean_date}) Tj ET')
    stream_ops.append('BT /F4 8 Tf 0.45 0.50 0.58 rg 70 105 Td (Registered in Fluence Academy Official Database) Tj ET')

    # 13. Center: Vector Official Seal Emblem
    cx, cy, r = 421, 126, 28
    k = 0.5522847498 * r
    stream_ops.append('0.82 0.68 0.21 RG 2 w')
    stream_ops.append(f'{cx} {cy+r} m {cx+k} {cy+r} {cx+r} {cy+k} {cx+r} {cy} c {cx+r} {cy-k} {cx+k} {cy-r} {cx} {cy-r} c {cx-k} {cy-r} {cx-r} {cy-k} {cx-r} {cy} c {cx-r} {cy+k} {cx-k} {cy+r} {cx} {cy+r} c S')
    r2 = 23
    k2 = 0.5522847498 * r2
    stream_ops.append('0.82 0.68 0.21 RG 0.75 w')
    stream_ops.append(f'{cx} {cy+r2} m {cx+k2} {cy+r2} {cx+r2} {cy+k2} {cx+r2} {cy} c {cx+r2} {cy-k2} {cx+k2} {cy-r2} {cx} {cy-r2} c {cx-k2} {cy-r2} {cx-r2} {cy-k2} {cx-r2} {cy} c {cx-r2} {cy+k2} {cx-k2} {cy+r2} {cx} {cy+r2} c S')
    seal_txt = 'FLUENCE'
    w_sl = len(seal_txt) * 5.0
    stream_ops.append(f'BT /F2 8 Tf 0.82 0.68 0.21 rg {cx-(w_sl/2):.1f} {cy+3:.1f} Td ({seal_txt}) Tj ET')
    seal_sub = 'ACADEMY'
    w_sls = len(seal_sub) * 4.4
    stream_ops.append(f'BT /F2 7 Tf 0.82 0.68 0.21 rg {cx-(w_sls/2):.1f} {cy-7:.1f} Td ({seal_sub}) Tj ET')

    # 14. Bottom Right: Director Signature Block
    sig_line_x = 590
    stream_ops.append(f'0.20 0.25 0.35 RG 1 w {sig_line_x} 145 m {sig_line_x+180} 145 l S')
    stream_ops.append(f'BT /F3 13 Tf 0.06 0.13 0.28 rg {sig_line_x+10} 150 Td (Lect. Mohammed Hussein) Tj ET')
    stream_ops.append(f'BT /F2 9.5 Tf 0.15 0.18 0.24 rg {sig_line_x} 131 Td (Lect. Mohammed Hussein) Tj ET')
    stream_ops.append(f'BT /F1 8.5 Tf 0.35 0.38 0.44 rg {sig_line_x} 118 Td (Director & General Academic Supervisor) Tj ET')
    stream_ops.append(f'BT /F4 8 Tf 0.45 0.50 0.58 rg {sig_line_x} 105 Td (Fluence English Academy) Tj ET')

    content = '\n'.join(stream_ops).encode('latin1')
    content_len = len(content)

    body = [
        b'%PDF-1.4',
        b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj',
        b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj',
        b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R /F4 7 0 R >> >> /Contents 8 0 R >>\nendobj',
        b'4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj',
        b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj',
        b'6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>\nendobj',
        b'7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic >>\nendobj',
        f'8 0 obj\n<< /Length {content_len} >>\nstream\n'.encode('latin1') + content + b'\nendstream\nendobj'
    ]

    xref_positions = []
    current_pos = 0
    raw_pdf = b''
    for obj in body:
        xref_positions.append(current_pos)
        raw_pdf += obj + b'\n'
        current_pos = len(raw_pdf)

    xref_start = len(raw_pdf)
    xref = [f'xref\n0 {len(body) + 1}\n0000000000 65535 f \n'.encode('latin1')]
    for pos in xref_positions:
        xref.append(f'{pos:010d} 00000 n \n'.encode('latin1'))

    trailer = f'trailer\n<< /Size {len(body) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n'.encode('latin1')

    final_data = raw_pdf + b''.join(xref) + trailer

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, 'wb') as f:
        f.write(final_data)

    return output_path
