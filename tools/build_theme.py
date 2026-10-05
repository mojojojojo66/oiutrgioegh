#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mediphera — بناء قالب Blogger النهائي
====================================
1) يضغط الصور ويحوّلها Base64 (تُضمّن داخل القالب فيصبح جاهزاً فوراً).
2) يحقن محتوى الأقسام القابلة للتعديل (HTML Widgets) محوّلاً إلى صيغة XML آمنة.
3) يتحقق من سلامة XML (well-formed) قبل الكتابة.
4) يستخرج CSS للقالب إلى preview/css/mediphera.css لمعاينة الموقع محلياً.

الاستخدام:  python3 tools/build_theme.py
"""
import base64
import io
import re
import sys
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "template" / "theme.template.xml"
OUT = ROOT / "mediphera-blogger-theme.xml"
CSS_OUT = ROOT / "preview" / "css" / "mediphera.css"

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("  ! تنبيه: PIL غير متوفر — ستُستخدم الصور بحجمها الأصلي")


def datauri(path: Path, target_w: int = None, quality: int = 82) -> str:
    data = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    if HAS_PIL:
        try:
            im = Image.open(io.BytesIO(data))
            if target_w and im.width > target_w:
                ratio = target_w / im.width
                im = im.resize((target_w, int(im.height * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            fmt = "PNG" if path.suffix.lower() == ".png" else "JPEG"
            if fmt == "JPEG" and im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.save(buf, format=fmt, quality=quality, optimize=True)
            data = buf.getvalue()
        except Exception as e:  # noqa: BLE001
            print(f"  ! فشل ضغط {path.name}: {e}")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def esc(s: str) -> str:
    """تحويل HTML إلى نص آمن داخل عنصر XML."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    tpl = TPL.read_text("utf-8")

    # (رمز الاستبدال، مسار الصورة، العرض الأقصى بالبكسل)
    images = {
        "__LOGO_B64__": ("assets/images/logo.png", 420),
        "__HERO_B64__": ("assets/images/hero.jpg", 1440),
        "__ABOUT_B64__": ("assets/images/about.jpg", 1080),
        "__PRODUCT_1_B64__": ("assets/images/product-vitamin-c.jpg", 760),
        "__PRODUCT_2_B64__": ("assets/images/product-niacinamide.jpg", 760),
        "__PRODUCT_3_B64__": ("assets/images/product-retinol.jpg", 760),
        "__PRODUCT_4_B64__": ("assets/images/product-salicylic.jpg", 760),
        "__PRODUCT_5_B64__": ("assets/images/product-hyaluronic.jpg", 760),
        "__PRODUCT_6_B64__": ("assets/images/product-shampoo.jpg", 760),
    }

    widgets = {
        "__WIDGET_ABOUT__": "template/content/about-section.html",
        "__WIDGET_PRODUCTS__": "template/content/products-section.html",
        "__WIDGET_FAQ__": "template/content/faq-section.html",
        "__WIDGET_CONTACT__": "template/content/contact-section.html",
    }

    print("1) تجهيز الصور (Base64)…")
    datauris = {}
    for tok, (rel, w) in images.items():
        uri = datauri(ROOT / rel, w)
        datauris[tok] = uri
        print(f"   {tok}: {len(uri) // 1024} KB")

    print("2) حقن محتوى الأقسام القابلة للتعديل…")
    for tok, rel in widgets.items():
        content = (ROOT / rel).read_text("utf-8")
        for t, uri in datauris.items():
            content = content.replace(t, uri)
        content = esc(content)
        if tok not in tpl:
            sys.exit(f"خطأ: الرمز {tok} غير موجود في القالب!")
        tpl = tpl.replace(tok, content)
        print(f"   {tok}: تم الحقن")

    print("3) حقن الصور المتبقية في القالب…")
    for tok, uri in datauris.items():
        if tok in tpl:
            tpl = tpl.replace(tok, uri)

    # التأكد من عدم بقاء أي رمز
    leftover = re.findall(r"__[A-Z0-9_]+__", tpl)
    leftover = [t for t in leftover if t != "__LOGO_URL__"]  # مقصود — يُستبدل يدوياً
    if leftover:
        sys.exit(f"خطأ: رموز متبقية: {sorted(set(leftover))}")

    print("4) التحقق من صحة XML…")
    xml.dom.minidom.parseString(tpl.encode("utf-8"))
    print("   XML well-formed ✓")

    OUT.write_text(tpl, "utf-8")
    print(f"5) كُتب القالب النهائي: {OUT.name} ({len(tpl.encode('utf-8')) // 1024} KB)")

    m = re.search(r"<b:skin><!\[CDATA\[(.*?)\]\]></b:skin>", tpl, re.S)
    if m:
        CSS_OUT.parent.mkdir(parents=True, exist_ok=True)
        CSS_OUT.write_text(m.group(1), "utf-8")
        print(f"6) كُتب CSS المعاينة: {CSS_OUT}")
    else:
        print("   ! تحذير: لم يتم العثور على b:skin لاستخراج CSS")

    print("تم البناء بنجاح ✓")


if __name__ == "__main__":
    main()
