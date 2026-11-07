"""
Fluence English Academy - Official PDF Certificate Generator
Generates strictly valid, high-resolution vector PDF certificates with the official Fluence Academy Logo embedded.
100% Pure Python (Zero external dependencies).
"""

import os
from datetime import datetime

def create_certificate_pdf(
    student_name: str,
    score: int,
    total_questions: int,
    level: str,
    cert_id: str,
    issue_date: str,
    output_path: str
) -> str:
    """Creates strictly valid Landscape A4 PDF certificate with embedded logo."""
    percentage = round((score / total_questions) * 100, 1) if total_questions > 0 else 0

    clean_name = ''.join(c for c in str(student_name) if 32 <= ord(c) <= 126).strip() or "Fluence Scholar"
    clean_level = ''.join(c for c in str(level) if 32 <= ord(c) <= 126).strip().upper() or "B2"
    clean_id = ''.join(c for c in str(cert_id) if 32 <= ord(c) <= 126).strip() or "FA-CEFR-2026-0001"
    clean_date = ''.join(c for c in str(issue_date) if 32 <= ord(c) <= 126).strip() or datetime.now().strftime("%Y-%m-%d")

    # البحث عن صورة الشعار
    logo_candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo_square.jpg"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.jpg"),
        os.path.join("app", "assets", "logo_square.jpg"),
        os.path.join("app", "assets", "logo.jpg"),
        "logo_square.jpg",
        "logo.jpg"
    ]
    logo_bytes = None
    for cand in logo_candidates:
        if os.path.exists(cand):
            try:
                with open(cand, 'rb') as lf:
                    logo_bytes = lf.read()
                break
            except Exception:
                pass

    stream_ops = []
    # الخلفية البيضاء
    stream_ops.append('1 1 1 rg 0 0 842 595 re f')
    # الإطارات الملكية (كحلي وذهبي)
    stream_ops.append('0.06 0.13 0.28 RG 6 w 25 25 792 545 re S')
    stream_ops.append('0.79 0.65 0.27 RG 2 w 35 35 772 525 re S')
    stream_ops.append('0.06 0.13 0.28 RG 0.8 w 41 41 760 513 re S')
    stream_ops.append('0.79 0.65 0.27 rg 33 33 12 12 re f 797 33 12 12 re f 33 550 12 12 re f 797 550 12 12 re f')

    # الشعار الرسمي أعلى الشهادة
    if logo_bytes:
        stream_ops.append('q 64 0 0 64 389 488 cm /Im1 Do Q')

    # ترويسة الأكاديمية
    stream_ops.append('BT /F2 18 Tf 0.06 0.13 0.28 rg 290 460 Td (FLUENCE ENGLISH ACADEMY) Tj ET')
    stream_ops.append('BT /F4 10 Tf 0.79 0.65 0.27 rg 305 444 Td (ACCREDITED LANGUAGE & ACADEMIC PLATFORM) Tj ET')
    stream_ops.append('BT /F3 26 Tf 0.08 0.16 0.35 rg 215 395 Td (CERTIFICATE OF PROFICIENCY) Tj ET')
    stream_ops.append('BT /F4 11 Tf 0.45 0.50 0.58 rg 270 375 Td (COMMON EUROPEAN FRAMEWORK OF REFERENCE - CEFR) Tj ET')
    stream_ops.append('BT /F1 12 Tf 0.35 0.38 0.44 rg 355 335 Td (This is to certify that) Tj ET')

    # اسم الطالب المسجل
    name_x = max(100, int(421 - (len(clean_name) * 11 / 2)))
    stream_ops.append(f'BT /F2 22 Tf 0.08 0.16 0.35 rg {name_x} 300 Td ({clean_name}) Tj ET')
    stream_ops.append('0.79 0.65 0.27 RG 1.5 w 250 292 m 592 292 l S')

    # البيان الأكاديمي
    stream_ops.append('BT /F1 11.5 Tf 0.25 0.28 0.34 rg 170 262 Td (has successfully completed the comprehensive diagnostic English placement assessment) Tj ET')
    stream_ops.append('BT /F1 11.5 Tf 0.25 0.28 0.34 rg 210 244 Td (demonstrating proven academic competence and linguistic proficiency evaluated at:) Tj ET')

    # وسام المستوى المعتمد
    stream_ops.append('0.06 0.13 0.28 rg 271 185 300 42 re f')
    stream_ops.append('0.79 0.65 0.27 RG 2 w 271 185 300 42 re S')
    badge_text = f'CEFR LEVEL: {clean_level}'
    badge_x = int(421 - (len(badge_text) * 8.5 / 2))
    stream_ops.append(f'BT /F2 15 Tf 1 1 1 rg {badge_x} 200 Td ({badge_text}) Tj ET')

    score_text = f'Official Assessment Score: {score}/{total_questions} - {percentage}%'
    score_x = int(421 - (len(score_text) * 6.5 / 2))
    stream_ops.append(f'BT /F2 10.5 Tf 0.08 0.16 0.35 rg {score_x} 165 Td ({score_text}) Tj ET')

    # بيانات التوثيق والتحقق
    stream_ops.append('0.79 0.65 0.27 RG 1 w 70 148 m 260 148 l S')
    stream_ops.append(f'BT /F2 9.5 Tf 0.15 0.18 0.24 rg 70 133 Td (Credential ID: {clean_id}) Tj ET')
    stream_ops.append(f'BT /F1 9 Tf 0.30 0.35 0.42 rg 70 119 Td (Issue Date: {clean_date}) Tj ET')
    stream_ops.append('BT /F4 8 Tf 0.45 0.50 0.58 rg 70 105 Td (Verified in Fluence Academy Notion Registry) Tj ET')

    # ختم الأكاديمية بالأسفل
    if logo_bytes:
        stream_ops.append('q 60 0 0 60 391 80 cm /Im1 Do Q')

    # توقيع الأستاذ المشرف العام
    stream_ops.append('0.79 0.65 0.27 RG 1 w 580 148 m 770 148 l S')
    stream_ops.append('BT /F2 9.5 Tf 0.15 0.18 0.24 rg 580 133 Td (Lect. Mohammed Hussein) Tj ET')
    stream_ops.append('BT /F1 8.5 Tf 0.35 0.38 0.44 rg 580 119 Td (Director & General Academic Supervisor) Tj ET')
    stream_ops.append('BT /F4 8 Tf 0.45 0.50 0.58 rg 580 105 Td (Fluence English Academy) Tj ET')

    content = '\n'.join(stream_ops).encode('latin1')
    content_len = len(content)

    res_dict = b'<< /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R /F4 7 0 R >>'
    if logo_bytes:
        res_dict += b' /XObject << /Im1 9 0 R >>'
    res_dict += b' >>'

    header = b'%PDF-1.4\n'
    objs = [
        b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj',
        b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj',
        b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources ' + res_dict + b' /Contents 8 0 R >>\nendobj',
        b'4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj',
        b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj',
        b'6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>\nendobj',
        b'7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic >>\nendobj',
        f'8 0 obj\n<< /Length {content_len} >>\nstream\n'.encode('latin1') + content + b'\nendstream\nendobj'
    ]

    if logo_bytes:
        objs.append(
            f'9 0 obj\n<< /Type /XObject /Subtype /Image /Width 477 /Height 477 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_bytes)} >>\nstream\n'.encode('latin1')
            + logo_bytes
            + b'\nendstream\nendobj'
        )

    raw = header
    offsets = []
    for obj in objs:
        offsets.append(len(raw))
        raw += obj + b'\n'

    xref_offset = len(raw)
    xref_str = f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'
    for off in offsets:
        xref_str += f'{off:010d} 00000 n \n'

    raw += xref_str.encode('latin1')
    raw += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('latin1')

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, 'wb') as f:
        f.write(raw)

    return output_path
