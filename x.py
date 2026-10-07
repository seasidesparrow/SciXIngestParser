import json
from glob import glob

from ingestparser.parsers.copernicus import CopernicusParser

files = glob("tests/stubdata/input/*coper*")


for f in files:
    with open(f, "r") as fin:
        raw = fin.read()
    parser = CopernicusParser()
    output = parser.parse(raw)
    outfile = f.split("/")[-1]+".json"
    with open(outfile, "w") as fout:
        fout.write("%s" % json.dumps(output, indent=2, sort_keys=True))
