from html import escape

MISSING_TEXT = "-"


def number(value, decimals=1):
    if value != value:
        return MISSING_TEXT
    return f"{value:,.{decimals}f}"


def signed(value, decimals=1):
    if value != value:
        return MISSING_TEXT
    return f"{value:+,.{decimals}f}"


def percent(value, decimals=0):
    if value != value:
        return MISSING_TEXT
    return f"{value:.{decimals}%}"


def text(value):
    if value != value or value is None:
        return MISSING_TEXT
    return escape(str(value))


def htmlTable(headers, rows, textColumns=1, cssClass=""):
    """Rows are lists of pre-formatted strings; the first textColumns columns are left-aligned."""
    def cells(values, tag):
        parts = []
        for position, value in enumerate(values):
            alignment = "left" if position < textColumns else "right"
            parts.append(f'<{tag} class="{alignment}">{value}</{tag}>')
        return "".join(parts)

    head = f"<tr>{cells(headers, 'th')}</tr>"
    body = "".join(f"<tr>{cells(row, 'td')}</tr>" for row in rows)
    return f'<table class="{cssClass}"><thead>{head}</thead><tbody>{body}</tbody></table>'


def figure(fileName, caption, cssClass=""):
    return (f'<figure class="{cssClass}"><img src="charts/{fileName}.png" alt="{escape(caption)}">'
            f"<figcaption>{caption}</figcaption></figure>")


def section(title, *blocks):
    return f"<section><h2>{title}</h2>{''.join(blocks)}</section>"


def paragraph(content):
    return f"<p>{content}</p>"


def bulletList(items):
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"
