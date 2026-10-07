#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فاحص قالب «دهشة موثّقة» قبل الرفع على بلوجر.
الاستخدام:  python3 tools/check-template.py [اسم الملف]

يفحص: سلامة XML، فضاءات أسماء بلوجر، تعريفات b:include، الأقسام والودجات،
متغيّرات السكِن (وجود الحقول الخمسة + شرط الوصف العربي)، المراجع $( ) المجهولة،
الخصائص الفيزيائية (RTL)، صحة JSON-LD، واستعمال أدوات data:view الحديثة.

ملاحظة: لا يحتوي على محلّل CSS كامل (tinycss2 اختياري إن كان مثبّتًا).
"""
import json
import re
import sys
import xml.etree.ElementTree as ET

PATH = sys.argv[1] if len(sys.argv) > 1 else "dahsha-muthaqa.xml"
xml = open(PATH, encoding="utf-8").read()
ok = True


def chk(cond, label, extra=""):
    global ok
    if not cond:
        ok = False
    print(("  ✅ " if cond else "  ❌ ") + label + ((" — " + str(extra)) if extra else ""))


Q = "['\"]"
ATTR_RE = re.compile(r"(\w[\w:-]*)\s*=\s*" + Q + r"([^'\"]*)" + Q)


def attrs(tag):
    return dict(ATTR_RE.findall(tag))


def tags(name):
    # نستبعد الوسوم المشابهة مثل <b:widget-settings> و <b:widget>...</b:widget>
    return re.findall(r"<" + name + r"(?=[\s/>])([^>]*?)/?>", xml)


print("— فحص", PATH, "—")

# 1) سلامة XML وترويسة بلوجر
ET.fromstring(xml)
chk(True, "XML سليم (well-formed)")
chk(
    "xmlns:b=" in xml and "xmlns:data=" in xml and "xmlns:expr=" in xml,
    "فضاءات أسماء Blogger معلنة",
)
chk(
    xml.count("<b:includable") == xml.count("</b:includable>"),
    "توازن وسوم b:includable",
    xml.count("<b:includable"),
)

# 2) تعريفات b:include المحلية
ids = set(re.findall(r"<b:includable\s+id=" + Q + r"([^'\"]+)", xml))
called = [a["name"] for a in (attrs(t) for t in tags("b:include")) if "name" in a]
# all-head-content و google-analytics من تعريفات بلوجر المدمجة (غير معرّفة في القالب)
BUILTIN = {"all-head-content", "google-analytics"}
missing = sorted(set(called) - ids - BUILTIN)
chk(
    not missing,
    "كل b:include المحلية لها تعريف",
    f"مفقود: {missing}" if missing else f"{len(called)} مرجعًا",
)

# 3) الأقسام والودجات
secs = [a["id"] for a in (attrs(t) for t in tags("b:section")) if "id" in a]
wids = [a["id"] for a in (attrs(t) for t in tags("b:widget")) if "id" in a]
chk(len(secs) == 6, "عدد الأقسام 6", secs)
chk(len(wids) == len(set(wids)), "معرّفات الودجات فريدة", wids)
flaw = []
for t in tags("b:widget"):
    a = attrs(t)
    # غياب version يعني الوراثة من b:defaultwidgetversion='2' (سلوك بلوجر القياسي)
    if a.get("version") not in (None, "1", "2") or not a.get("type") or not a.get("id"):
        flaw.append(a.get("id"))
chk(not flaw, "كل الودجات تحمل type، وversion صالح/موروث", flaw)

# 4) متغيّرات السكِن
m = re.search(r"<b:skin[^>]*><!\[CDATA\[(.*?)\]\]></b:skin>", xml, re.S)
skin = m.group(1)
vs = [attrs(t) for t in re.findall(r"<Variable\b([^>]*?)/?>", skin)]
need = {"name", "description", "type", "default", "value"}
chk(
    all(need <= set(v) for v in vs),
    "كل متغيّر يحمل name/description/type/default/value",
    f"{len(vs)} متغيّرًا",
)
bad = [v["name"] for v in vs if not re.fullmatch(r"[\u0600-\u06FF\s]{1,40}", v.get("description", ""))]
chk(not bad, "أوصاف المتغيّرات عربية بسيطة (شرط بلوجر)", bad)
known = {v["name"] for v in vs} | {v["name"].split(".")[0] for v in vs}
# متغيّرات نوعها font تمنح بلوجر تلقائيًّا: family/size/weight/style/line.height
for v in vs:
    if v.get("type") == "font":
        for sub in ("family", "size", "weight", "style", "line.height"):
            known.add(v["name"] + "." + sub)
unknown = [
    u
    for u in sorted(set(re.findall(r"\$\(([^()]+)\)", skin)))
    if u not in known and u != "color" and not re.search(r"[*/+-]", u)
]
chk(not unknown, "لا مراجع $( ) مجهولة", unknown)

# 5) نظافة CSS / الاتجاه المنطقي
phys = re.findall(r"(?<![\w-])(?:left|right)\s*:", skin)
phys += re.findall(r"(?<![\w-])(?:margin|padding|border)-(?:left|right)\s*:", skin)
chk(not phys, "لا خصائص فيزيائية (RTL منطقي)", phys[:5])
chk(skin.count("{") == skin.count("}"), "توازن أقواس CSS", f"{skin.count('{')}/{skin.count('}')}")

# 6) JSON-LD و data:view
for i, blk in enumerate(
    re.findall(r"<script type=" + Q + r"application/ld\+json" + Q + r">(.*?)</script>", xml, re.S)
):
    try:
        # نُفكّ ترميز XML ثم نُزيل وسوم بلوجر (<data:.../> و <b:eval .../>) قبل التحقّق
        plain = (
            blk.replace("&quot;", '"')
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        plain = re.sub(r"<b:eval\b.*?/?>", "X", plain, flags=re.S)
        plain = re.sub(r"<data:[^>]*/>", "X", plain)
        # القالب قد يحتوي <b:if> داخل JSON: نتحقّق من الحالتين (الشرط صحيح/خاطئ)
        with_if = re.sub(r"</?b:if\b[^>]*>", "", plain)          # الشرط صحيح
        without_if = re.sub(r"<b:if\b.*?</b:if>", "", plain, flags=re.S)  # الشرط خاطئ
        json.loads(with_if)
        json.loads(without_if)
        chk(True, f"JSON-LD #{i + 1} صالح")
    except Exception as e:  # noqa: BLE001
        chk(False, f"JSON-LD #{i + 1}", e)
chk("data:view.is" in xml, "يستعمل data:view الحديثة")
chk(not re.search(r"<b:widget[^>]*type=" + Q + r"HTML", xml), "لا ودجات HTML (لا سكربتات غريبة)")
ver = attrs(re.search(r"<html\b[^>]*>", xml).group(0)).get("b:templateVersion", "")
chk(re.fullmatch(r"\d+\.\d+\.\d+", ver or ""), "b:templateVersion بصيغة صحيحة", ver)

# 7) محلّل CSS اختياري (tinycss2)
try:
    import tinycss2  # type: ignore
except ImportError:
    print("  ℹ️  tinycss2 غير مثبّت — تخطّي التحليل اللغوي لـ CSS (pip install tinycss2)")
else:
    vals = {v["name"]: v["value"] for v in vs}

    def sub(mm):
        key = mm.group(1)
        if re.search(r"[*/+-]", key):
            try:
                flat = re.sub(r"[A-Za-z][\w.]*", lambda n: vals.get(n.group(0), "16").replace("px", ""), key)
                return str(round(eval(flat), 2)) + "px"  # noqa: S307
            except Exception:  # noqa: BLE001
                return "16px"
        return vals.get(key, vals.get(key.split(".")[0], "16px"))

    css = re.sub(r"\$\(([^()]*)\)", sub, skin).replace("$(color)", "#f7f4ee")
    n_err = 0
    for label, text in (("b:skin", css), ("b:template-skin", re.search(r"<b:template-skin><!\[CDATA\[(.*?)\]\]></b:template-skin>", xml, re.S).group(1))):
        rules = tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True)
        errs = [r for r in rules if r.type == "error"]
        inner = []
        for r in rules:
            if r.type == "qualified-rule":
                for d in tinycss2.parse_declaration_list(r.content, skip_comments=True, skip_whitespace=True):
                    if d.type == "error":
                        inner.append(d.message)
        n_err += len(errs) + len(inner)
        print(f"  ℹ️  {label}: {len(rules)} قاعدة CSS")
        for e in (errs + inner)[:8]:
            print("     !", e)
    chk(n_err == 0, "لا أخطاء نحوية في CSS", n_err)

print("\nالنتيجة:", "نجاح كامل ✅" if ok else "يوجد فشل ❌")
sys.exit(0 if ok else 1)
