import re
from xml.etree import ElementTree as ET

SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)

ALLOWED_TAGS = {
    'svg', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'path',
    'text', 'tspan', 'g', 'defs', 'lineargradient', 'radialgradient', 'stop',
    'clippath', 'title', 'desc',
}

DISALLOWED_ATTRS = {'href', 'xlink:href'}


def _local_tag(tag: str) -> str:
    return (tag.split('}')[-1] if '}' in tag else tag).lower()


def _local_attr(attr: str) -> str:
    return (attr.split('}')[-1] if '}' in attr else attr).lower()


def _strip_wrapper(markup: str) -> str:
    markup = markup.strip()
    markup = re.sub(r'^```(svg|xml)?\s*', '', markup)
    markup = re.sub(r'```\s*$', '', markup)
    return markup.strip()


def _clean_element(el):
    for attr in list(el.attrib):
        local = _local_attr(attr)
        if local.startswith('on') or local in DISALLOWED_ATTRS:
            del el.attrib[attr]

    for child in list(el):
        if _local_tag(child.tag) not in ALLOWED_TAGS:
            el.remove(child)
            continue
        _clean_element(child)


def sanitize_svg(markup: str) -> str | None:
    """Убирает опасные теги/атрибуты (script, image, обработчики событий, внешние ссылки)
    из SVG, сгенерированного AI, перед тем как рендерить его как markup в шаблоне.
    Возвращает None, если markup невалиден или это не SVG.
    """
    if not markup:
        return None

    markup = _strip_wrapper(markup)

    try:
        root = ET.fromstring(markup)
    except ET.ParseError:
        return None

    if _local_tag(root.tag) != 'svg':
        return None

    # Гарантируем корректный SVG-namespace на корне, даже если модель его не указала —
    # иначе автономная сериализация (для экспорта в PNG) не распознаётся как валидный SVG.
    if not root.tag.startswith('{'):
        root.tag = f'{{{SVG_NS}}}svg'

    _clean_element(root)
    return ET.tostring(root, encoding='unicode')
