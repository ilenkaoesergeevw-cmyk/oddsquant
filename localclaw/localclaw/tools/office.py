import os


def _require_windows():
    if os.name != "nt":
        raise RuntimeError("Office 控制仅支持 Windows（需要安装 pywin32）")


def _client(prog):
    _require_windows()
    import win32com.client

    return win32com.client.Dispatch(prog)


def word_create(path, text=""):
    app = _client("Word.Application")
    app.Visible = True
    doc = app.Documents.Add()
    if text:
        doc.Content.Text = text
    abs_path = os.path.abspath(path)
    doc.SaveAs(abs_path)
    return {"path": abs_path}


def word_append(path, text):
    app = _client("Word.Application")
    doc = app.Documents.Open(os.path.abspath(path))
    doc.Content.InsertAfter("\n" + text)
    doc.Save()
    return {"path": os.path.abspath(path)}


def ppt_create(path, slides):
    app = _client("PowerPoint.Application")
    app.Visible = True
    prs = app.Presentations.Add()
    for s in slides or []:
        slide = prs.Slides.Add(prs.Slides.Count + 1, 2)
        if s.get("title"):
            slide.Shapes.Title.TextFrame.TextRange.Text = s["title"]
        bullets = s.get("bullets") or []
        if bullets:
            slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = "\n".join(bullets)
    abs_path = os.path.abspath(path)
    prs.SaveAs(abs_path)
    return {"path": abs_path, "slides": len(slides or [])}
