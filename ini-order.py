import re
import sys

argv = sys.argv[1:]

# infile = argv[0]
# outfile = argv[1]

sections = {}
cursectname = ""
cursectlines = []

with open(argv[0],"r") as infile:
    for line in infile:
        if re.match(r"^\[([^\]]+)\]$",line):
            sections[cursectname] = cursectlines
            cursectname = line.strip()
            cursectlines = [line]
        else:
            cursectlines.append(line)
    sections[cursectname] = cursectlines

leadsects = [
    "",
    "[defaults]",
    "[base_efiction]",
    "[base_xenforoforum]",
    "[base_xenforoforum:epub]",
    "[epub]",
    "[html]",
    "[txt]",
    "[mobi]",
    "[test1.com]",
    "[test1.com:txt]",
    "[test1.com:html]",
    "[teststory:defaults]",
    "[teststory:1000]",
    "[overrides]",
    ]
followsects = [
    ]

with open(argv[1],"w") as outfile:
    kl = sections.keys()
    kl.sort()
    for k in leadsects:
        outfile.write("".join(sections[k]))

    for k in kl:
        if k not in (leadsects + followsects):
            outfile.write("".join(sections[k]))

    for k in followsects:
        outfile.write("".join(sections[k]))
