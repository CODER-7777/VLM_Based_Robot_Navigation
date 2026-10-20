"""Behavioral checks for blind separation, multi-answer grading, and review decisions."""
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from http.server import HTTPServer

from model import Catalog,DIMENSIONS,when
from server import App,handler

ROOT=Path(__file__).resolve().parent

class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.app=App(ROOT/'source',cls.tmp.name)
        cls.http=HTTPServer(('127.0.0.1',0),handler(cls.app));cls.url=f'http://127.0.0.1:{cls.http.server_port}'
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()

    def request(self,path,data=None,author=False):
        headers={'Content-Type':'application/json'}
        if author:headers['Cookie']='step8_author='+self.app.key
        req=Request(self.url+path,data=json.dumps(data).encode() if data else None,headers=headers)
        try:
            with urlopen(req,timeout=3) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)

    def test_all_cases_and_temporal_separation(self):
        c=self.app.catalog;self.assertEqual(len(c.cases),40);self.assertEqual(len(c.naturalness),62)
        for case in c.cases:
            for memory in c.memories(case,True):self.assertLess(when(memory),when(case['start']))

    def test_blind_redaction_all_cases(self):
        code,catalog=self.request('/api/catalog?mode=blind');self.assertEqual(code,200)
        self.assertNotIn('types',catalog);self.assertNotIn('reviews',catalog)
        for c in catalog['cases']:
            self.assertEqual(set(c),{'id','number'})
            _,case=self.request('/api/case?mode=blind&id='+c['id'])
            for k in ['expected','primary','secondary','flags','props','level1','phenomenon','length']:self.assertNotIn(k,case)
            for m in case['memories']:
                for k in ['roles','view','view_pose','used_by']:self.assertNotIn(k,m)

    def test_private_endpoints_protected(self):
        for p in ['/api/nav/map?token=anything','/api/catalog?mode=review','/api/case?mode=review&id=2azQ1b91cZZ_case01','/api/export','/api/props','/assets/sheet_room0.jpg']:
            self.assertEqual(self.request(p)[0],403)

    def test_exclusion_accepts_full_answer_sets(self):
        c=self.app.catalog
        self.assertEqual({x['id'] for x in c.case('2azQ1b91cZZ_case25')['expected']['level3']},{'p42','p43','p26'})
        self.assertEqual({x['id'] for x in c.case('2azQ1b91cZZ_case26')['expected']['level3']},{'room2','room7'})

    def test_off_limits_includes_memory_identifying_the_forbidden_room(self):
        catalog=self.app.catalog;moments={m['id']:m for m in catalog.week['moments']}
        for number,expected in [(1,'B01'),(6,'T02'),(17,'T15')]:
            c=catalog.by_id[f'2azQ1b91cZZ_case{number:02}'];form=catalog.case(c['case_id'])['forms'][0]
            self.assertEqual(form['room_memory_ids'],[expected])
            m=moments[expected];self.assertLess(when(m),when(c['start']))
            self.assertGreaterEqual(math.dist(m['view_pose']['xyz'][::2],c['end_xyz'][::2]),2)
            self.assertIn('room to avoid',next(m for m in catalog.memories(c) if m['id']==expected)['roles'])

    def test_first_stop_memories_are_present_and_earlier(self):
        catalog=self.app.catalog;moments={m['id']:m for m in catalog.week['moments']}
        count=0
        for c in catalog.cases:
            for form in catalog.case(c['case_id'])['forms']:
                if not (form.get('goal1') or form.get('first')):continue
                count+=1
                self.assertTrue(form['first_stop_memory_ids'],c['case_id'])
                for mid in form['first_stop_memory_ids']:self.assertLess(when(moments[mid]),when(c['start']))
        self.assertEqual(count,13)
        first=catalog.case('2azQ1b91cZZ_case02')['forms'][0]
        self.assertEqual(first['first_stop_memory_ids'],['T08']);self.assertTrue(first['first_stop_direct'])
        self.assertFalse(catalog.case('2azQ1b91cZZ_case05')['forms'][0]['first_stop_direct'])

    def review_body(self):
        return dict(reviewer='test',case_id='2azQ1b91cZZ_case01',variant='level3',ratings={k:'pass' for k in DIMENSIONS},walked=True,note='')

    def test_minor_ambiguity_prevents_pass(self):
        d=self.review_body();d['ratings']['memory']='minor';d['note']='Alias could refer to two rooms.'
        code,r=self.request('/api/review',d,True);self.assertEqual(code,200);self.assertEqual(r['decision'],'minor')

    def test_cannot_pass_without_walk_or_required_prop(self):
        d=self.review_body();d['walked']=False;self.assertEqual(self.request('/api/review',d,True)[0],400)
        d['walked']=True;d['case_id']='2azQ1b91cZZ_case03';d['variant']='form0';self.assertEqual(self.request('/api/review',d,True)[0],400)

    def test_props_gate_applies_only_to_the_selected_request(self):
        d=self.review_body();d['case_id']='2azQ1b91cZZ_case03'
        self.assertEqual(self.request('/api/review',d,True)[0],200)
        d['variant']='level2';self.assertEqual(self.request('/api/review',d,True)[0],200)
        d.update(case_id='2azQ1b91cZZ_case07',variant='level3');self.assertEqual(self.request('/api/review',d,True)[0],400)

    def test_cannot_skip_core_checks(self):
        d=self.review_body();d['ratings']['instruction']='na';self.assertEqual(self.request('/api/review',d,True)[0],400)

    def test_blind_answers_saved_separately_per_variant(self):
        d=dict(reviewer='independent',case_id='2azQ1b91cZZ_case01',answer='Game room',confidence='clear',variant='level3')
        self.assertEqual(self.request('/api/blind',d)[0],200)
        d.update(variant='level2',answer='Any available TV room');self.assertEqual(self.request('/api/blind',d)[0],200)
        self.assertEqual(len([k for k in self.app.records['blind'] if k.startswith('independent|')]),2)

    def test_only_judgments_written(self):
        files={p.name for p in Path(self.tmp.name).iterdir()}
        self.assertLessEqual(files,{'author_key','judgments.json'})

    def test_path_traversal_and_labelled_photos_blocked(self):
        for p in ['/assets/memory_T01_labels.jpg','/assets/../../server.py']:
            self.assertEqual(self.request(p)[0],404)

if __name__=='__main__':unittest.main(verbosity=2)
