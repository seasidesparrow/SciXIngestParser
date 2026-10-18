import json
from glob import glob

infiles=glob("tests/stubdata/output/*json")

for f in infiles:
    with open(f, "r") as fin:
        rawdata = fin.read()
    output = json.loads(rawdata)
    title = output.get("title", None)
    subtitle = output.get("subtitle", None)
    newput = {"title": title, "subtitle": subtitle}
    try:
        title.get("textEnglish", None)
    except:
        print("%s\n%s\n\n\n" % (f, json.dumps(newput, indent=2, sort_keys=True)))
