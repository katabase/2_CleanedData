import sys
import json
import re


def main(filename):
    final_dict = {}
    with open(filename, 'r') as fichier:  # liste qui correspond au fichier complet
        for line in fichier.read().splitlines():
            inter_dict = {}
            splitted_lines = line.split(",")
            for item in splitted_lines:
                analyze = re.search('([0-3][0-9])/([0-1][0-9])/([1][7-8][0-9][0-9])', item)
                print(item)
                print(analyze)
                if analyze is not None:
                    year = analyze.group(3)
                    month = analyze.group(2)
                    day = analyze.group(1)
                    inter_dict[splitted_lines.index(item)+1] = "%s-%s-%s" % (year,month,day)
                if analyze is None:
                    inter_dict[splitted_lines.index(item)+1] = "none"
            print(inter_dict)
            inter_dict.pop(1)
            final_dict[splitted_lines[0]] = inter_dict
    dict_to_json(final_dict)


def dict_to_json(dictionnary):
    with open('../json/corresp_table.json', 'w') as outfile:
        outfile.truncate(0)
        json.dump(dictionnary, outfile)


if __name__ == "__main__":
    main(sys.argv[1])