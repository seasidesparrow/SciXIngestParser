import json
from ingestparser.parsers.jats import JATSParser

infile = "/Users/mtemple/Projects/Github_repos/JATSFullTextParser/apj_976_1_106.xml"

with open(infile, "r") as fi:
    rawdata = fi.read()

p = JATSParser()
output = p.parse(rawdata)
outfile = infile.split("/")[-1]+".json"
with open(outfile, "w") as fo:
    fo.write("%s\n" % json.dumps(output, indent=2, sort_keys=True))
