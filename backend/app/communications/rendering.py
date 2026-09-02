from __future__ import annotations

import html
import io
import json
import fitz


def render_deterministic(template_subject:str|None,template_body:str,context:dict)->dict:
    safe={k:str(v) for k,v in context.items()}
    subject=template_subject.format_map(safe) if template_subject else None
    body=template_body.format_map(safe)
    sections=[{"heading":"Decision notice","text":body},{"heading":"Appeal rights","text":safe.get("appeal_rights","")},{"heading":"Human authority","text":safe.get("human_authority_statement","")}]
    accessible_html="<article aria-label=\"Medical claim decision notice\">"+"".join(f"<section><h2>{html.escape(s['heading'])}</h2><p>{html.escape(s['text'])}</p></section>" for s in sections)+"</article>"
    return {"subject":subject,"body_text":body,"accessible_html":accessible_html,"sections":sections,"language":safe.get("locale","en")}


def render_pdf_bytes(rendered:dict, *, title:str="Medical Claim Decision Notice")->bytes:
    doc=fitz.open(); page=doc.new_page(width=612,height=792)
    y=54
    page.insert_text((54,y),title,fontsize=16); y+=32
    for section in rendered.get("sections",[]):
        page.insert_text((54,y),section.get("heading",""),fontsize=12); y+=18
        text=section.get("text","")
        rect=fitz.Rect(54,y,558,min(740,y+150)); page.insert_textbox(rect,text,fontsize=10); y=min(740,y+120)
        if y>700: page=doc.new_page(width=612,height=792); y=54
    metadata=doc.metadata or {}; metadata.update({"title":title,"subject":"Human-released medical claim communication","keywords":"MedClaimIQ,accessible-text-alternative"}); doc.set_metadata(metadata)
    out=doc.tobytes(garbage=4,deflate=True); doc.close(); return out


def stable_json_bytes(value:object)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
