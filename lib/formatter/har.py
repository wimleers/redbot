#!/usr/bin/env python

"""
HAR Formatter for REDbot.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2010 Mark Nottingham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import datetime
try:
    import json
except ImportError:
    import simplejson as json 

import redbot.speak as rs
from nbhttp import get_hdr
from redbot import droid
from redbot.formatter import Formatter


class HarFormatter(Formatter):
    """
    Format a RED object (and any descendants) as HAR.
    """
    can_multiple = True
    name = "har"
    media_type = "application/json"
    
    def __init__(self, *args, **kw):
        Formatter.__init__(self, *args, **kw)
        self.har = {
            'log': {
                "version": "1.1",
                "creator": {
                    "name": "REDbot",
                    "version": droid.__version__,
                },
                "browser": {
                    "name": "REDbot",
                    "version": droid.__version__,
                },
                "pages": [],
                "entries": [],
            },
        }
        self.last_id = 0

    def start_output(self):
        pass
        
    def status(self, msg):
        pass

    def feed(self, red, sample):
        pass

    def finish_output(self, ired):
        "Fill in the template with RED's results."
        page_id = self.add_page(ired)
        self.add_entry(ired, page_id)
        for linked_red in [d[0] for d in ired.link_droids]:
            self.add_entry(linked_red, page_id)
        self.output(json.dumps(self.har, indent=4))
        
    def add_entry(self, red, page_ref=None):
        entry = {
            "startedDateTime": isoformat(red.req_ts),
            "time": int((red.res_done_ts - red.req_ts) * 1000),
            "_red_messages": self.format_messages(red)
        }
        if page_ref:
            entry['pageref'] = "page%s" % page_ref
        
        request = {
            'method': red.method,
            'url': red.uri,
            'httpVersion': "HTTP/1.1",
            'cookies': [],
            'headers': self.format_headers(red.req_hdrs),
            'queryString': [],
            'headersSize': -1,
            'bodySize': -1,
        }
        
        response = {
            'status': red.res_status,
            'statusText': red.res_phrase,
            'httpVersion': "HTTP/%s" % red.res_version, 
            'cookies': [],
            'headers': self.format_headers(red.res_hdrs),
            'content': {
                'size': red.res_body_decode_len,
                'compression': red.res_body_decode_len - red.res_body_len,
                'mimeType': (get_hdr(red.res_hdrs, 'content-type') or [""])[0],
            },
            'redirectURL': (get_hdr(red.res_hdrs, 'location') or [""])[0],
            'headersSize': red.client.input_header_length,
            'bodySize': red.res_body_len,
        }
        
        cache = {}
        timings = {
            'dns': -1,
            'connect': -1,
            'blocked': 0,
            'send': 0, 
            'wait': int((red.res_ts - red.req_ts) * 1000),
            'receive': int((red.res_done_ts - red.res_ts) * 1000),
        }

        entry.update({
            'request': request,
            'response': response,
            'cache': cache,
            'timings': timings,
        })
        self.har['log']['entries'].append(entry)

        
    def add_page(self, red):
        page_id = self.last_id + 1
        page = {
            "startedDateTime": isoformat(red.req_ts),
            "id": "page%s" % page_id,
            "title": "",
            "pageTimings": {
                "onContentLoad": -1,
                "onLoad": -1,
            },
        }
        self.har['log']['pages'].append(page)
        return page_id

    def format_headers(self, hdrs):
        return [ {'name': n, 'value': v} for n, v in hdrs ]

    def format_messages(self, red):
        out = []
        for m in red.messages:
            msg = {
                "subject": m.subject,
                "category": m.category,
                "level": m.level,
                "summary": m.summary[self.lang] % m.vars
            }
            smsgs = [i for i in getattr(
                m.subrequest, "messages", []) if i.level in [rs.l.BAD]]
            msg["subrequests"] = \
            [{
                "subject": sm.subject,
                "category": sm.category,
                "level": sm.level,
                "summary": sm.summary[self.lang]
            } for sm in smsgs]
            out.append(msg)
        return out

def isoformat(timestamp):
    class TZ(datetime.tzinfo):
        def utcoffset(self, dt): 
            return datetime.timedelta(minutes=0)
    return "%sZ" % datetime.datetime.utcfromtimestamp(timestamp).isoformat()
      