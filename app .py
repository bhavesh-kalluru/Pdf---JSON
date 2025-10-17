import io
import json
import os
import re
from typing import Dict, Any, Tuple, List, Optional

import streamlit as st

# ---------------------- Extraction helpers ----------------------

def extract_text_pdfplumber(file_bytes: bytes) -> str:
    try:
        import pdfplumber
    except Exception:
        return ""
    text_pages = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                text_pages.append(txt.strip())
    except Exception:
        return ""
    text = "\n".join(p for p in text_pages if p)
    return text.strip()

def extract_text_ocr_pdf2image(file_bytes: bytes) -> str:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except Exception:
        return ""
    try:
        images = convert_from_bytes(file_bytes, dpi=300)
    except Exception:
        return ""
    ocr_texts = []
    for img in images:
        try:
            ocr_texts.append(pytesseract.image_to_string(img))
        except Exception:
            continue
    return "\n".join(ocr_texts).strip()

def extract_text_ocr_pymupdf(file_bytes: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
    except Exception:
        return ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return ""
    texts = []
    for page in doc:
        try:
            pix = page.get_pixmap(dpi=300, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texts.append(pytesseract.image_to_string(img))
        except Exception:
            continue
    return "\n".join(texts).strip()

def extract_text(file_bytes: bytes, ocr_mode: str = "auto") -> Tuple[str, str, Dict[str, bool]]:
    diags = {
        "has_pdfplumber": False,
        "has_pdf2image": False,
        "has_pymupdf": False,
        "has_pytesseract": False,
    }

    # Check imports for diagnostics only (do not fail here)
    try:
        import pdfplumber  # noqa
        diags["has_pdfplumber"] = True
    except Exception:
        pass
    try:
        from pdf2image import convert_from_bytes  # noqa
        diags["has_pdf2image"] = True
    except Exception:
        pass
    try:
        import fitz  # noqa
        diags["has_pymupdf"] = True
    except Exception:
        pass
    try:
        import pytesseract  # noqa
        diags["has_pytesseract"] = True
    except Exception:
        pass

    # 1) Try text-based extraction
    text = extract_text_pdfplumber(file_bytes)
    if text and len(text) >= 100:
        return text, "pdfplumber", diags

    # 2) OCR fallback
    if ocr_mode == "off":
        return "", "disabled", diags

    if ocr_mode == "pdf2image":
        ocr_text = extract_text_ocr_pdf2image(file_bytes)
        if ocr_text:
            return ocr_text, "ocr(pdf2image+tesseract)", diags
        return "", "ocr_failed", diags

    if ocr_mode == "pymupdf":
        ocr_text = extract_text_ocr_pymupdf(file_bytes)
        if ocr_text:
            return ocr_text, "ocr(pymupdf+tesseract)", diags
        return "", "ocr_failed", diags

    # auto: try pdf2image then pymupdf
    ocr_text = extract_text_ocr_pdf2image(file_bytes)
    if not ocr_text:
        ocr_text = extract_text_ocr_pymupdf(file_bytes)
        if ocr_text:
            return ocr_text, "ocr(pymupdf+tesseract)", diags
    else:
        return ocr_text, "ocr(pdf2image+tesseract)", diags

    return "", "ocr_failed", diags

# ---------------------- Parsing helpers ----------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,2}\s*)?(?:\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4})")
URL_RE = re.compile(r"(https?://[^\s]+|(?:www\.)?[A-Za-z0-9\-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[A-Za-z0-9/_\-]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_\-]+", re.I)


DATE_WORDS = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December|Present|Current|\\d{4}"
DATE_RANGE_RE = re.compile(
    rf"(({DATE_WORDS})\\.?\\s?\\d{{0,4}})\\s?(?:–|-|—|to)\\s?(({DATE_WORDS})\\.?\\s?\\d{{0,4}})",
    re.I
)

BULLET_RE = re.compile(r"^\\s*(?:[-•▪‣*]|\\d+\\.)\\s+")

SECTION_TITLES = [
    "experience", "work experience", "professional experience",
    "education",
    "projects",
    "skills", "technical skills", "skills & technologies",
    "certifications", "licenses",
    "publications",
    "awards", "honors",
    "summary", "profile", "objective",
]

def guess_name(lines: List[str], email_line_idx: int) -> str:
    candidates = []
    for line in lines[: min(5, len(lines))]:
        clean = line.strip()
        if not clean:
            continue
        if clean.isupper() or clean.istitle():
            if clean.lower() not in SECTION_TITLES:
                candidates.append(clean)
    if candidates:
        return candidates[0]
    for line in lines:
        if line.strip():
            return line.strip()
    return ""

def extract_contact_info(text: str) -> Dict[str, Any]:
    lines = [l for l in text.splitlines() if l.strip()]
    joined = " | ".join(lines)

    emails = EMAIL_RE.findall(joined)
    phones = PHONE_RE.findall(joined)
    urls = URL_RE.findall(joined)

    linkedin = [u for u in urls if LINKEDIN_RE.search(u)]
    github = [u for u in urls if GITHUB_RE.search(u)]

    email_idx = 0
    for idx, line in enumerate(lines[:15]):
        if EMAIL_RE.search(line):
            email_idx = idx
            break

    name = guess_name(lines, email_idx)

    return {
        "name": name or None,
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "urls": list(dict.fromkeys(urls)),
        "linkedin": linkedin[0] if linkedin else None,
        "github": github[0] if github else None,
    }

def find_sections(text: str) -> Dict[str, str]:
    indices = []
    for title in SECTION_TITLES:
        pattern = re.compile(rf"(?m)^\\s*{re.escape(title)}\\s*:?\\s*$", re.I)
        for match in pattern.finditer(text):
            indices.append((match.start(), title))
    if not indices:
        return {"body": text}

    indices.sort()
    sections = {}
    for i, (start, title) in enumerate(indices):
        end = indices[i + 1][0] if i + 1 < len(indices) else len(text)
        section_text = text[start:end].strip()
        sections[title.lower()] = section_text
    return sections

def parse_bullets(block: str) -> List[str]:
    bullets = []
    for line in block.splitlines():
        if BULLET_RE.match(line):
            bullets.append(BULLET_RE.sub("", line).strip())
    if not bullets:
        parts = re.split(r"(?<=[\\.\\!\\?])\\s+(?=[A-Z])", block.strip())
        bullets = [p.strip() for p in parts if len(p.strip()) > 0]
    return bullets

def parse_experience(section_text: str) -> List[Dict[str, Any]]:
    lines = section_text.splitlines()
    if lines and lines[0].strip().lower().startswith(("experience","work experience","professional experience")):
        lines = lines[1:]

    experiences = []
    buffer: List[str] = []

    def flush_buffer():
        nonlocal buffer, experiences
        block = "\\n".join(buffer).strip()
        if not block:
            return
        blines = [l for l in block.splitlines() if l.strip()]
        header = blines[0] if blines else ""
        parts = re.split(r"\\s+[—\\-–]\\s+|\\s+\\|\\s+", header)
        role, company = None, None
        if len(parts) == 2:
            left, right = parts
            if re.search(r"engineer|manager|developer|scientist|consultant|intern|analyst|lead|architect", left, re.I):
                role, company = left.strip(), right.strip()
            else:
                company, role = left.strip(), right.strip()
        else:
            cparts = [p.strip() for p in header.split(",") if p.strip()]
            if len(cparts) >= 2:
                role, company = cparts[0], ", ".join(cparts[1:])
            else:
                role = header.strip()

        dr = DATE_RANGE_RE.search(block)
        start_date, end_date = (dr.group(1), dr.group(2)) if dr else (None, None)

        location = None
        for l in blines[:3]:
            if re.search(r"[A-Za-z]+,\\s*[A-Za-z]+", l) and not EMAIL_RE.search(l):
                location = l.strip()
                break

        bullets = parse_bullets("\\n".join(blines[1:]))
        experiences.append({
            "company": company,
            "role": role,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "highlights": bullets
        })
        buffer = []

    for line in lines:
        if DATE_RANGE_RE.search(line) and buffer:
            flush_buffer()
        buffer.append(line)
    if buffer:
        flush_buffer()
    return experiences

def parse_education(section_text: str) -> List[Dict[str, Any]]:
    lines = section_text.splitlines()
    if lines and lines[0].strip().lower().startswith("education"):
        lines = lines[1:]
    entries = []
    block = "\\n".join(lines)
    for chunk in re.split(r"\\n\\s*\\n", block):
        clines = [c.strip() for c in chunk.splitlines() if c.strip()] or []
        if not clines:
            continue
        header = clines[0]
        degree = None
        institution = None
        parts = re.split(r"\\s+[—\\-–]\\s+|\\s+\\|\\s+", header)
        if len(parts) == 2:
            left, right = parts
            if re.search(r"B\\.?S|B\\.?E|M\\.?S|M\\.?Eng|M\\.?Tech|B\\.?Tech|Ph\\.?D|Bachelor|Master|Doctor|Associate", left, re.I):
                degree, institution = left.strip(), right.strip()
            else:
                institution, degree = left.strip(), right.strip()
        else:
            cparts = [p.strip() for p in header.split(",") if p.strip()]
            if len(cparts) >= 2:
                institution, degree = cparts[0], ", ".join(cparts[1:])
            else:
                institution = header

        dr = DATE_RANGE_RE.search(chunk)
        start_date, end_date = (dr.group(1), dr.group(2)) if dr else (None, None)

        gpa = None
        m = re.search(r"GPA\\s*[:\\-]?\\s*([0-9]\\.\\d{1,2})", chunk, re.I)
        if m:
            gpa = m.group(1)

        entries.append({
            "institution": institution,
            "degree": degree,
            "start_date": start_date,
            "end_date": end_date,
            "gpa": gpa
        })
    return entries

def parse_skills(section_text: str) -> List[str]:
    lines = section_text.splitlines()
    if lines and lines[0].strip().lower().startswith(("skills","technical skills","skills & technologies")):
        section_text = "\\n".join(lines[1:])
    parts = re.split(r"[,|;\\n]", section_text)
    skills = [p.strip(" -•\\t") for p in parts if p.strip()]
    seen = set()
    dedup = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            dedup.append(s)
            seen.add(key)
    return dedup

def parse_projects(section_text: str) -> List[Dict[str, Any]]:
    lines = section_text.splitlines()
    if lines and lines[0].strip().lower().startswith("projects"):
        lines = lines[1:]
    projects = []
    chunk = []
    def flush():
        nonlocal chunk, projects
        if not chunk:
            return
        block = "\\n".join(chunk).strip()
        plines = [l for l in block.splitlines() if l.strip()]
        title = plines[0] if plines else "Project"
        bullets = parse_bullets("\\n".join(plines[1:]))
        url = None
        m = URL_RE.search(block)
        if m: url = m.group(0)
        projects.append({"title": title, "url": url, "details": bullets})
        chunk = []
    for line in lines:
        if line.strip() == "":
            flush()
        else:
            chunk.append(line)
    flush()
    return projects

def parse_sections_to_json(sections: Dict[str, str]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if any(k in sections for k in ("experience","work experience","professional experience")):
        key = next((k for k in ("experience","work experience","professional experience") if k in sections), None)
        data["experience"] = parse_experience(sections[key])
    if "education" in sections:
        data["education"] = parse_education(sections["education"])
    if any(k in sections for k in ("skills","technical skills","skills & technologies")):
        key = next((k for k in ("skills","technical skills","skills & technologies") if k in sections), None)
        data["skills"] = parse_skills(sections[key])
    if "projects" in sections:
        data["projects"] = parse_projects(sections["projects"])
    for k in ("certifications","licenses","publications","awards","honors","summary","profile","objective"):
        if k in sections:
            data[k.replace(" & ", "_and_").replace(" ", "_")] = sections[k]
    return data

def build_json(text: str, method: str) -> Dict[str, Any]:
    contact = extract_contact_info(text)
    sections = find_sections(text)
    structured = parse_sections_to_json(sections)
    return {
        "extraction_method": method,
        "raw_text_preview": text[:1000],
        "contact": contact,
        **structured
    }

# ---------------------- Streamlit UI ----------------------

st.set_page_config(page_title="Resume PDF → JSON", page_icon="📄", layout="centered")

st.title("📄 Resume PDF → JSON")
st.write("Upload a resume PDF, parse it to structured JSON, and download the result.")

uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])

col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    run_btn = st.button("Convert")
with col2:
    show_text = st.checkbox("Show raw text preview", value=False)
with col3:
    ocr_toggle = st.checkbox("Enable OCR fallback", value=True)
with col4:
    ocr_engine = st.selectbox("OCR engine", ["auto","pdf2image","pymupdf","off"], index=0, help="Use 'pymupdf' if Poppler isn't installed")

if run_btn and uploaded is None:
    st.warning("Please upload a PDF first.")

if uploaded and run_btn:
    file_bytes = uploaded.read()
    mode = "auto" if ocr_toggle else "off"
    if ocr_engine != "auto":
        mode = ocr_engine

    text, method, diags = extract_text(file_bytes, ocr_mode=mode)

    with st.expander("Diagnostics"):
        st.write(diags)
        st.write({"method_used": method, "text_length": len(text) if text else 0})

    if not text:
        st.error("Could not extract text. If the PDF is a scan, try switching OCR engine to 'pymupdf' or ensure Tesseract and Poppler are installed (see notes below).")
    else:
        data = build_json(text, method)
        st.success(f"Parsed using: {method}")

        if show_text:
            st.subheader("Raw Text Preview (first 1000 chars)")
            st.text(data.get("raw_text_preview", "") or "")

        st.subheader("JSON Output")
        st.json(data)

        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        default_name = os.path.splitext(uploaded.name)[0] + "_parsed.json"
        st.download_button(
            label="⬇️ Download JSON",
            data=json_bytes,
            file_name=default_name,
            mime="application/json"
        )

st.markdown("---")
st.markdown("**Notes**")
st.markdown(
    "- Text extraction uses `pdfplumber`; if the PDF is scanned, enable OCR fallback.\\n"
    "- OCR engines supported: `pdf2image + pytesseract` (needs **Poppler** + **Tesseract**) or `PyMuPDF + pytesseract` (no Poppler needed).\\n"
    "- Install on macOS with Homebrew: `brew install tesseract poppler` (for pdf2image path).\\n"
    "- Or use PyMuPDF route (no Poppler): `pip install pymupdf pytesseract`. Still requires Tesseract installed."
)
