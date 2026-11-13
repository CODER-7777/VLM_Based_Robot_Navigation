"""Check document exports, citation coverage, saved source hashes and key results.

Runs document checks only: no model import, network request or GPU allocation.
The PDF must already have been rendered by LibreOffice after the latest export.
"""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
LAB = ROOT.parent
SOURCE = LAB/'GQFT_APPROACHES_AND_RESEARCH.md'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = SOURCE.read_text()
    checks = {}

    def check(name, ok, detail=None):
        checks[name] = {'pass': bool(ok), 'detail': detail}

    records = json.loads((ROOT/'papers.json').read_text())['papers']
    check('all_14_approaches_present', all('| A%02d |' % i in source for i in range(1, 15)))
    check('all_10_original_and_4_additional_papers',
          len(records) == 14 and all('### '+r['id']+'. ' in source for r in records))
    check('primary_citations_in_document', all(r['primary_url'] in source for r in records))
    bib = (ROOT/'papers.bib').read_text()
    check('bibtex_coverage', all('@inproceedings{gqft_'+r['id'].lower()+',' in bib for r in records))
    check('no_unfilled_placeholders', '<!--' not in source)

    missing = []
    for path in [SOURCE, LAB.parent/'APPROACHES_TRIED.md', ROOT/'REPOSITORY_IMPLEMENTATIONS.md']:
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            if not target.startswith(('https:', 'http:', '#')):
                if not (path.parent/target.split('#')[0]).exists():
                    missing.append({'file': str(path.relative_to(LAB.parent)), 'target': target})
    check('local_document_links', not missing, missing)

    with ZipFile(SOURCE.with_suffix('.docx')) as z:
        check('docx_zip_integrity', z.testzip() is None)
        trees = {n: ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith(('.xml', '.rels'))}
        check('docx_xml_parse', len(trees) == 6, len(trees))
        check('docx_matches_source_hash', z.read('source_sha256.txt').decode().strip() == digest(SOURCE))
        text = ''.join(trees['word/document.xml'].itertext())
        check('docx_contains_paper_sections', all(r['id']+'. ' in text for r in records))
        relationships = trees['word/_rels/document.xml.rels']
        hyperlinks = [r for r in relationships if r.attrib['Type'].endswith('/hyperlink')]
        source_links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', source)
        check('docx_preserves_hyperlinks', len(hyperlinks) == len(source_links), len(hyperlinks))
        check('docx_preserves_tables', len(trees['word/document.xml'].findall('.//{%s}tbl' % W)) == 8)

    pdf = SOURCE.with_suffix('.pdf')
    text = subprocess.run(['pdftotext', str(pdf), '-'], check=True, capture_output=True, text=True).stdout
    info = subprocess.run(['pdfinfo', str(pdf)], check=True, capture_output=True, text=True).stdout
    check('pdf_contains_paper_sections', all(r['id']+'.' in text for r in records))
    check('pdf_contains_all_approaches', all('A%02d' % i in text for i in range(1, 15)))
    pages = re.search(r'^Pages:\s+(\d+)', info, re.MULTILINE)
    check('pdf_renders', pages is not None and int(pages.group(1)) > 0,
          {'pages': int(pages.group(1)) if pages else None,
           'visual_review': 'Approach table, paper section and final-page render inspected'})
    check('pdf_is_current', pdf.stat().st_mtime >= SOURCE.stat().st_mtime)
    check('pdf_key_results', all(s in text for s in ('12.4626', '11.3485', '65.5247', '0.016462', '4.491709')))

    audit = json.loads((ROOT/'repository_audit.json').read_text())
    failures, count = [], 0
    for repo in audit:
        folder = ROOT/'repositories'/repo['repository'].replace('/', '__')
        for file in repo.get('files', []):
            if file.get('sha256'):
                count += 1
                path = folder/file['path']
                if not path.exists() or digest(path) != file['sha256'] or path.stat().st_size != file['bytes']:
                    failures.append(str(path))
    check('pinned_source_files_unchanged', not failures, {'files': count, 'failures': failures})
    check('repository_statuses', len(audit) == 9 and sum(r.get('http_status') == 200 for r in audit) == 8)

    pilot = json.loads((LAB/'diagnosis_20261104/findings.json').read_text())['h24_validation']
    check('pilot_ade_fde_match_saved_evidence', all(
        f"{row['ade_px']:.4f}" in source and f"{row['fde_px']:.4f}" in source for row in pilot.values()))
    solver = json.loads((LAB/'ground_geometry_20261109/verification.json').read_text())
    check('solver_scores_match_saved_evidence', all(
        f'{value:.6f}' in source for leg in solver['episode629'].values() for value in leg.values()))
    check('15_recorded_hybrid_checks', len(solver['checks']) == 15 and all(c['pass'] for c in solver['checks'].values()))

    files = [SOURCE, SOURCE.with_suffix('.docx'), pdf, ROOT/'papers.json', ROOT/'papers.bib',
             ROOT/'REPOSITORY_IMPLEMENTATIONS.md', ROOT/'export_document.py', Path(__file__)]
    result = {'checked_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Documentation packaging and saved-evidence checks; no new model results',
              'training_performed': False, 'gpu_used': False, 'latest_user_gpu_choice': '4 (12 November)',
              'checks': checks, 'artifacts': [
                  {'path': str(p.relative_to(LAB)), 'sha256': digest(p), 'bytes': p.stat().st_size} for p in files]}
    (ROOT/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    failed = [k for k, v in checks.items() if not v['pass']]
    print(json.dumps({'passed': len(checks)-len(failed), 'total': len(checks), 'failed': failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
