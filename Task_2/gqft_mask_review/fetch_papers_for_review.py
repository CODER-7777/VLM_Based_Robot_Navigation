"""Fetch primary PDFs into /tmp for reading; publish only access receipts/notes."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

LAB=Path(__file__).resolve().parent
OUT=LAB/'SOLVER_REVIEW/research_next_attempts_20261113'
TEMP=Path('/tmp/gqft_papers_review_20261113')
URLS={
'P01':'https://arxiv.org/pdf/1805.11913',
'P02':'https://arxiv.org/pdf/1804.07723',
'P03':'https://arxiv.org/pdf/1806.03589',
'P04':'https://arxiv.org/pdf/1811.09935',
'P05':'https://arxiv.org/pdf/2011.00359',
'P06':'https://arxiv.org/pdf/2208.04726',
'P07':'https://arxiv.org/pdf/1704.00390',
'P08':'https://arxiv.org/pdf/1909.00512',
'P09':'https://arxiv.org/pdf/1702.01417',
'P10':'https://proceedings.mlr.press/v202/garrido23a/garrido23a.pdf',
'P11':'https://vladlen.info/papers/deep-fundamental.pdf',
'P12':'https://arxiv.org/pdf/2108.10869',
'P13':'https://publications.ri.cmu.edu/storage/publications/pub_files/pub4/ke_qifa_2003_1/ke_qifa_2003_1.pdf',
'P14':'https://rpg.ifi.uzh.ch/docs/ICRA09_scaramuzza.pdf'}


def fetch(item):
    key,url=item;pdf=TEMP/(key+'.pdf');text=TEMP/(key+'.txt')
    try:
        if not pdf.exists():
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 GQFT research review'})
            with urllib.request.urlopen(req,timeout=50) as response:content=response.read()
            if not content.startswith(b'%PDF'):raise ValueError('Response is not a PDF')
            pdf.write_bytes(content)
        subprocess.run(['pdftotext','-layout',str(pdf),str(text)],check=True,capture_output=True)
        content=text.read_text()
        return {'id':key,'url':url,'downloaded':True,'pdf_bytes':pdf.stat().st_size,
                'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
                'extracted_pages':content.count('\f'),'extracted_words':len(content.split()),
                'local_reading_copy':str(text),'scope':'Access/extraction receipt, not a claim that every line was reviewed'}
    except Exception as error:return {'id':key,'url':url,'downloaded':False,'error':str(error)}


def main():
    OUT.mkdir(exist_ok=True);TEMP.mkdir(exist_ok=True);results=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(fetch,item) for item in URLS.items()]):
            r=future.result();results.append(r);print(r['id'],r['downloaded'],r.get('extracted_pages',r.get('error')),flush=True)
            (OUT/'paper_reading_sources.json').write_text(json.dumps(sorted(results,key=lambda r:r['id']),indent=2)+'\n')


if __name__=='__main__':main()
