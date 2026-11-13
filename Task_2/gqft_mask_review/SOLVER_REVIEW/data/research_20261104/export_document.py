"""Export the consolidated Markdown to DOCX using only the Python standard library.

This handles the headings, paragraphs, lists, fenced text, links and tables used
by this document. It does not execute code blocks or access the network.
"""
import argparse
import hashlib
import re
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
ET.register_namespace('w', W)
ET.register_namespace('r', R)


def el(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, '{%s}%s' % (W, tag),
                         {'{%s}%s' % (W, k): str(v) for k, v in attrs.items()})
    if text is not None:
        node.text = text
    return node


def xml(node):
    return ET.tostring(node, encoding='utf-8', xml_declaration=True)


class Exporter:
    def __init__(self):
        self.document = ET.Element('{%s}document' % W)
        self.body = el(self.document, 'body')
        self.rels = ET.Element('Relationships', xmlns=P)
        for ident, kind, target in [('styles', 'styles', 'styles.xml'),
                                    ('footer', 'footer', 'footer1.xml')]:
            ET.SubElement(self.rels, 'Relationship', Id=ident,
                          Type=R + '/' + kind, Target=target)
        self.link_count = 0
        self.table_count = 0

    def run(self, parent, text, bold=False, code=False, link=False):
        node = el(parent, 'r')
        if bold or code or link:
            prop = el(node, 'rPr')
            if bold:
                el(prop, 'b')
            if code:
                el(prop, 'rFonts', ascii='DejaVu Sans Mono', hAnsi='DejaVu Sans Mono')
                el(prop, 'sz', val=17)
            if link:
                el(prop, 'color', val='176B8C')
                el(prop, 'u', val='single')
        t = el(node, 't', text)
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

    def inline(self, parent, text, bold=False):
        pattern = r'\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*'
        start = 0
        for match in re.finditer(pattern, text):
            self.run(parent, text[start:match.start()], bold=bold)
            if match.group(1) is not None:
                self.link_count += 1
                ident = 'link' + str(self.link_count)
                target = quote(match.group(2), safe='/:#?=&%+@,;~')
                ET.SubElement(self.rels, 'Relationship', Id=ident,
                              Type=R + '/hyperlink', Target=target, TargetMode='External')
                link = el(parent, 'hyperlink')
                link.set('{%s}id' % R, ident)
                self.run(link, match.group(1), bold=bold, link=True)
            elif match.group(3) is not None:
                self.run(parent, match.group(3), code=True)
            else:
                self.run(parent, match.group(4), bold=True)
            start = match.end()
        self.run(parent, text[start:], bold=bold)

    def paragraph(self, text, style=None, parent=None, code=False, bold=False):
        p = el(self.body if parent is None else parent, 'p')
        if style:
            el(el(p, 'pPr'), 'pStyle', val=style)
        if code:
            self.run(p, text, code=True)
        else:
            self.inline(p, text, bold=bold)
        return p

    def table(self, lines):
        rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
        rows = [r for r in rows if not all(re.fullmatch(r':?-+:?', c) for c in r)]
        count = len(rows[0])
        weights = {2: [0.34, 0.66], 3: [0.34, 0.33, 0.33],
                   4: [0.10, 0.24, 0.18, 0.48],
                   5: [0.30, 0.16, 0.16, 0.22, 0.16]}.get(count, [1/count]*count)
        # Three-column source tables need a wider first column than numeric tables.
        if count == 3 and rows[0][0] in ('Protocol', 'Proposal'):
            weights = [0.25, 0.47, 0.28]
        widths = [int(w*9360) for w in weights]
        table = el(self.body, 'tbl')
        self.table_count += 1
        prop = el(table, 'tblPr')
        el(prop, 'tblW', w=9360, type='dxa')
        el(prop, 'tblLayout', type='fixed')
        borders = el(prop, 'tblBorders')
        for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el(borders, edge, val='single', sz=4, color='D2DEE5')
        margins = el(prop, 'tblCellMar')
        for edge in ('top', 'left', 'bottom', 'right'):
            el(margins, edge, w=80, type='dxa')
        grid = el(table, 'tblGrid')
        for width in widths:
            el(grid, 'gridCol', w=width)
        for index, row in enumerate(rows):
            tr = el(table, 'tr')
            if index == 0:
                el(el(tr, 'trPr'), 'tblHeader')
            for i, text in enumerate(row):
                cell = el(tr, 'tc')
                cp = el(cell, 'tcPr')
                el(cp, 'tcW', w=widths[i], type='dxa')
                if index == 0:
                    el(cp, 'shd', fill='E4F0F5')
                self.paragraph(text, style='TableText', parent=cell, bold=index == 0)
        self.paragraph('')

    def parse(self, text):
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip() or line.startswith('<!--'):
                i += 1
                continue
            if line.startswith('```'):
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    self.paragraph(lines[i], style='Code', code=True)
                    i += 1
                i += 1
                continue
            if line.startswith('|'):
                group = []
                while i < len(lines) and lines[i].startswith('|'):
                    group.append(lines[i]); i += 1
                self.table(group)
                continue
            heading = re.match(r'^(#{1,3}) (.*)$', line)
            if heading:
                level = len(heading.group(1))
                self.paragraph(heading.group(2), style='Title' if level == 1 else 'Heading'+str(level-1))
            elif re.match(r'^\d+\. ', line) or line.startswith('- '):
                self.paragraph(line, style='ListParagraph')
            else:
                self.paragraph(line)
            i += 1

    def save(self, destination, source_sha):
        sect = el(self.body, 'sectPr')
        footer = el(sect, 'footerReference', type='default')
        footer.set('{%s}id' % R, 'footer')
        el(sect, 'pgSz', w=11906, h=16838)
        el(sect, 'pgMar', top=1100, right=1273, bottom=1100, left=1273, header=400, footer=400)
        styles = ET.Element('{%s}styles' % W)
        defaults = el(styles, 'docDefaults')
        rp = el(el(defaults, 'rPrDefault'), 'rPr')
        el(rp, 'rFonts', ascii='DejaVu Sans', hAnsi='DejaVu Sans')
        el(rp, 'sz', val=20)
        pp = el(el(defaults, 'pPrDefault'), 'pPr')
        el(pp, 'spacing', after=100, line=270, lineRule='auto')
        for ident, name, size, color in [('Title', 'Title', 36, '173B50'),
                ('Heading1', 'Heading 1', 28, '173B50'), ('Heading2', 'Heading 2', 23, '176B8C'),
                ('TableText', 'Table Text', 17, '173040'), ('Code', 'Code', 17, '173040'),
                ('ListParagraph', 'List Paragraph', 20, '173040')]:
            style = el(styles, 'style', type='paragraph', styleId=ident)
            el(style, 'name', val=name)
            prop = el(style, 'pPr')
            if ident in ('Title', 'Heading1', 'Heading2'):
                el(prop, 'keepNext')
                el(prop, 'spacing', before=200, after=110)
            elif ident == 'Code':
                el(prop, 'spacing', after=0, line=220, lineRule='auto')
            elif ident == 'TableText':
                el(prop, 'spacing', after=40, line=225, lineRule='auto')
            rp = el(style, 'rPr'); el(rp, 'sz', val=size); el(rp, 'color', val=color)
            if ident.startswith('Heading') or ident == 'Title':
                el(rp, 'b')
        footer = ET.Element('{%s}ftr' % W)
        p = el(footer, 'p')
        self.run(p, 'GQFT approaches and research | 12 November 2026 | ')
        field = el(p, 'fldSimple', instr='PAGE')
        self.run(field, '1')
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>'''
        root_rels = ET.Element('Relationships', xmlns=P)
        ET.SubElement(root_rels, 'Relationship', Id='document', Type=R+'/officeDocument', Target='word/document.xml')
        with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
            archive.writestr('[Content_Types].xml', content_types)
            archive.writestr('_rels/.rels', xml(root_rels))
            archive.writestr('word/document.xml', xml(self.document))
            archive.writestr('word/styles.xml', xml(styles))
            archive.writestr('word/footer1.xml', xml(footer))
            archive.writestr('word/_rels/document.xml.rels', xml(self.rels))
            archive.writestr('source_sha256.txt', source_sha+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent.parent/'GQFT_APPROACHES_AND_RESEARCH.md')
    args = parser.parse_args()
    data = args.source.read_bytes()
    exporter = Exporter()
    exporter.parse(data.decode('utf-8'))
    out = args.source.with_suffix('.docx')
    exporter.save(out, hashlib.sha256(data).hexdigest())
    print(f'{out}: {exporter.table_count} tables, {exporter.link_count} hyperlinks')


if __name__ == '__main__':
    main()
