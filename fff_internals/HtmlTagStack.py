# coding: utf-8

import re
import codecs

stack = []

def get_end_tag(tag):
    if len(tag) > 0 and tag.find(u'<') > -1 and tag.rfind(u'>') > -1:
        return re.sub(r'.*<([^\ >]+).*', r'</\1>', tag)
    return u''

def get_tag_name(tag):
    if len(tag) > 0 and tag.find(u'<') > -1 and tag.rfind(u'>') > -1:
        return re.sub(r'</*([^\ >]+).*', r'\1', tag)
    return u''

def push(tag):
    if len(tag) > 0 and tag.find(u'<') > -1 and tag.rfind(u'>') > -1:
        stack.append(tag)

def pop():
    if len(stack) > 0:
        return stack.pop()
    return u''

def pop_end_tag():
    return unicode(get_end_tag(pop()))

def spool_end():
    html = u''
    for tag in reversed(stack):
        html += get_end_tag(tag)
    return html

def spool_start():
    html = u''
    for item in stack:
        html += item
    return html

def has_elements():
    return len(stack) > 0

def get_last():
    # t = pop()
    # push(t)
    # return t
    if len(stack) > 0:
        return stack[len(stack)-1]
    return u''

def flush():
    del stack[:]

def get_stack():
    return stack