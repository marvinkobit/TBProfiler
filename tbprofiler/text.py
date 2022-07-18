import time
from unittest import result
from pathogenprofiler import get_summary
from pathogenprofiler import errlog, debug, unlist, dict_list2text
from .utils import get_drug_list
import jinja2

def lineagejson2text(x):
    textlines = []
    for l in x:
        textlines.append("%(lin)s\t%(family)s\t%(spoligotype)s\t%(rd)s\t%(frac)s" % l)
    return "\n".join(textlines)

default_template = """
TBProfiler report
=================

The following report has been generated by TBProfiler.

Summary
-------
ID{{d['sep']}}{{d['id']}}
Date{{d['sep']}}{{d['date']}}
Strain{{d['sep']}}{{d['strain']}}
Drug-resistance{{d['sep']}}{{d['drtype']}}
Median Depth{{d['sep']}}{{d['med_dp']}}

Lineage report
--------------
{{d['lineage_report']}}
{% if 'spacers' in d %}
Spoligotype report
------------------
Binary{{d['sep']}}{{d['binary']}}
Octal{{d['sep']}}{{d['octal']}}
Family{{d['sep']}}{{d['family']}}
SIT{{d['sep']}}{{d['SIT']}}
{% endif %}
Resistance report
-----------------
{{d['dr_report']}}

Resistance variants report
-----------------
{{d['dr_var_report']}}

Other variants report
---------------------
{{d['other_var_report']}}

Coverage report
---------------------
{{d['coverage_report']}}

Missing positions report
---------------------
{{d['missing_report']}}
{% if 'spacers' in d %}
Spoligotype spacers
-------------------
{{d['spacers']}}
{% endif %}
Analysis pipeline specifications
--------------------------------
Pipeline version{{d['sep']}}{{d['version']}}
Database version{{d['sep']}}{{d['db_version']}}
{{d['pipeline']}}

Citation
--------
Coll, F. et al. Rapid determination of anti-tuberculosis drug resistance from
whole-genome sequences. Genome Medicine 7, 51. 2015

Phelan, JE. et al. Integrating informatics tools and portable sequencing 
technology for rapid detection of resistance to anti-tuberculous drugs. 
Genome Medicine 11, 41. 2019
"""

def load_text(text_strings,template = None):
    if template==None:
        template = default_template
    else:
        template = open(template).read()

    t =  jinja2.Template(template)
    return t.render(d=text_strings)

def stringify_annotations(annotation):
    annotations = []
    for ann in annotation:
        annotations.append("|".join([f'{key}={val}' for key,val in ann.items()]))
    return ";".join(annotations)

def write_text(json_results,conf,outfile,columns = None,reporting_af = 0.0,sep="\t",add_annotations=True,template_file = None):
    text_strings = json_results
    text_strings["id"] = json_results["id"]
    text_strings["date"] = time.ctime()
    if "dr_variants" in json_results:
        if add_annotations:
            for var in json_results["dr_variants"] + json_results["other_variants"]:
                if "annotation" in var:
                    var["annotation_str"] = stringify_annotations(var["annotation"])
                else:
                    var["annotation_str"] = ""

        json_results = get_summary(json_results,conf,columns = columns,reporting_af=reporting_af)
        drug_list = get_drug_list(conf["bed"])

        json_results["drug_table"] = [[y for y in json_results["drug_table"] if y["Drug"].upper()==d.upper()][0] for d in conf["drugs"] if d in drug_list]
        for var in json_results["dr_variants"]:
            var["drug"] = "; ".join([d["drug"] for d in var["drugs"]])

        text_strings["dr_report"] = dict_list2text(json_results["drug_table"],["Drug","Genotypic Resistance","Mutations"]+columns if columns else [],sep=sep)
        text_strings["dr_var_report"] = dict_list2text(json_results["dr_variants"],mappings={"genome_pos":"Genome Position","locus_tag":"Locus Tag","gene":"Gene","type":"Variant type","change": "Change","freq":"Estimated fraction","drugs.drug":"Drug"},sep=sep)
        text_strings["other_var_report"] = dict_list2text(json_results["other_variants"],mappings={"genome_pos":"Genome Position","locus_tag":"Locus Tag","gene":"Gene","type":"Variant type","change": "Change","freq":"Estimated fraction","annotation_str":"Annotation"},sep=sep)
        text_strings["drtype"] = json_results["drtype"]
       

    if "sublin" in json_results:
        text_strings["strain"] = json_results["sublin"]
        text_strings["lineage_report"] = dict_list2text(json_results["lineage"],["lin","frac","family","spoligotype","rd"],{"lin":"Lineage","frac":"Estimated fraction"},sep=sep)
        
    if "qc" in json_results:
        text_strings["med_dp"] = json_results["qc"]["median_coverage"] if json_results['input_data_source'] in ('bam','fastq') else "NA"
        text_strings["coverage_report"] = dict_list2text(json_results["qc"]["gene_coverage"], ["gene","locus_tag","cutoff","fraction"],sep=sep) if "gene_coverage" in json_results["qc"] else "Not available"
        text_strings["missing_report"] = dict_list2text(json_results["qc"]["missing_positions"],["gene","locus_tag","position","variants","drugs"],sep=sep) if "missing_positions" in json_results["qc"] else "Not available"
    if "spoligotype" in json_results:
        text_strings["binary"] = json_results["spoligotype"]["binary"]
        text_strings["octal"] = json_results["spoligotype"]["octal"]
        text_strings["SIT"] = json_results["spoligotype"]["SIT"]
        text_strings["family"] = json_results["spoligotype"]["family"]
        text_strings["spacers"] = dict_list2text(json_results["spoligotype"]["spacers"],["name","count"])
    

        
    text_strings["pipeline"] = dict_list2text(json_results["pipeline"],["Analysis","Program"],sep=sep)
    text_strings["version"] = json_results["tbprofiler_version"]
    tmp = json_results["db_version"]
    text_strings["db_version"] = "%s_%s_%s_%s" % (tmp["name"],tmp["commit"],tmp["Author"],tmp["Date"])
    if sep=="\t":
        text_strings["sep"] = ": "
    else:
        text_strings["sep"] = ","
    with open(outfile,"w") as O:
        O.write(load_text(text_strings,template_file))