from ..query_render import render_text


def render(desc, rows, file, *, dcontext, **kwargs):
    if not rows:
        return
    return render_text(desc, rows, dcontext, file, **kwargs)
