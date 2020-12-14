#!/usr/bin/python
# coding: utf-8
import shutil
import os
import glob
import re
import dateparser
import datetime
from decimal import *
import tables.rep_greg_conversion
import tables.conversion_tables
from dateparser.search import search_dates

import argparse
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("input", help="input directory")
args = arg_parser.parse_args()

# Module used to parse XML files.
from lxml import etree
import xml.etree.ElementTree as ET
from xml.etree import ElementTree

# Module used to note errors in a .log file.
import logging
logging.basicConfig(filename='errors.log', level=logging.DEBUG, filemode="w", format="%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s")

tei = {'tei': 'http://www.tei-c.org/ns/1.0'}



def price_extractor(descList):
    """
    Extracts the prices of the manuscripts sold and described in the tei:desc.
    :param descList: the list containing all of the tei:desc
    :return: a dict with the ids as keys, and value another dict with the prices
    """
    print("Extracting price information")
    output_dict = {}
    for item in descList:
        desc, id = item[0], item[1]
        pre_extracted_price = item[-1]
        if pre_extracted_price is not None:
            pattern = re.compile("[0-9]{0,3}\.[0-9]{0,2}")
            if pattern.match(item[-1]):
                try:
                    price = float(item[-1])
                except Exception as e:
                	logging.info('Failed to parse price %s for id : %s', e, id)
                	price = None
            else:
                try:
                    price = int(item[-1])
                except Exception as j:
                    logging.info('Failed to parse price %s for id : %s', j, id)
                    price = None
        else:
            price = None
        desc = clean_text(desc)
        dict_values = {"desc": desc}
        dict_values["price"] = price
        dict_values["author"] = item[2]
        desc_xml = desc
        output_dict[id] = dict_values
        item[0] = desc_xml
    return (output_dict)



def date_extractor(descList, input_dict):
    """
    Extracts the dates from the list containing all of the tei:desc, and update the main dict.
    :param descList: the list containing all of the tei:desc
    :param input_dict: the dictionnary containing the data previously extracted (at this moment, only the price)
    :return: a dict which keys are the ids, and which values are another dict with prices and dates
    """
    print("Extracting date information")
    for item in descList:
        desc, id = item[0], item[1]
        desc = clean_text(desc)
        # We search for any series of four digits (as a gregorian date)
        loose_gregorian_calendar_pattern = re.compile(
            ".*(1[0-9][0-9][0-9]).*")
        # We search for any hint of the republication calendar (as "an" and roman numerals)
        republican_calendar_pattern = re.compile(
            ".*\san ([XIVxiv]{1,4}|[0-9]{1,2}).*")

        dict_values = input_dict[id]
        date_log_path = None
        date_range = None
        desc_xml = desc

        # Let's extract the gregorian calendar dates.
        # Example: "Pièce de vers aut. sig. sig. aussi par sa femme Caroline Vanhove: 18 janvier 1798, 1 p. in-8 obl. 22"
        if loose_gregorian_calendar_pattern.match(desc):
            date_log_path = 1
            """First, we start reducing the string with a first split using the comma as delimiter, as (usually) there
            is no comma in a date:
            ['Pièce de vers aut. sig. sig. aussi par sa femme Caroline Vanhove: 18 janvier 1798', ' 1 p. in-8 obl. 22']"""
            tokenizedDesc = desc.split(",")
            string_list = []
            for tok_item in tokenizedDesc:
                if loose_gregorian_calendar_pattern.match(tok_item):
                    string_list.append(tok_item)
            """We can reduce the list to its last element: it will contain the date, as (usually) there is only a
            single date:
            ['Pièce de vers aut. sig. sig. aussi par sa femme Caroline Vanhove: 18 janvier 1798']"""
            string_list = string_list[-1]

            # Second, we can reduce the string using the semi colon as delimiter.
            # In our example, it won't affect the string.
            string_list = string_list.split(";")
            for elem in string_list:
                if loose_gregorian_calendar_pattern.match(elem):
                    string_list = elem
            # We split the string by the date, keeping it. The year beeing the delimiter, everything after it is not
            # a date. No change in our example
            string_list = re.split("(1[0-9][0-9][0-9])", string_list)
            string_list = string_list[:-1]
            date_string = ''.join([str(elem) for elem in string_list])
            # Strip is used to remove leading and trailing spaces.
            unprocessed_date_string = date_string.strip()

            # Third, we reduce the string using the colon as delimiter.
            # '18 janvier 1798'
            date_string = date_string.split(":")
            for elem in date_string:
                if loose_gregorian_calendar_pattern.match(elem):
                    date_string = elem
            # Etc.
            date_string = date_string.split("(")
            for elem in date_string:
                if loose_gregorian_calendar_pattern.match(elem):
                    date_string = elem

            date_string = date_string.split("«")
            for elem in date_string:
                if loose_gregorian_calendar_pattern.match(elem):
                    date_string = elem

            date_string = date_string.split(">")
            for elem in date_string:
                if loose_gregorian_calendar_pattern.match(elem):
                    date_string = elem

            # Then we clean the string
            date_string = re.sub(r'\s+', ' ', date_string)
            date_string = re.sub(r'\(', '', date_string)
            date_string = re.sub(r'L\. a\. s\.', '', date_string)
            # And eventually we can extract the date as a string to process it
            date = re.sub(r'^\s', '', date_string)

            # This pattern matches strings that contains only a year.
            gregorian_year_pattern = re.compile("^1[0-9][0-9][0-9]$")  
            # If the date is a year and nothing else, no need to process it.
            if gregorian_year_pattern.match(date):
                date_log_path = 2
                matched = re.finditer(gregorian_year_pattern, date)
                for match in matched:
                    desc_xml = desc.replace(match.group(0), f'<date \
                           xmlns=\u0022http://www.tei-c.org/ns/1.0\u0022 when=\u0022{date}\u0022>{match.group(0)}</date>')
            else:
            # To extrat the date automatically, we use the dateparser library.
            # see https://dateparser.readthedocs.io/en/v0.2.1/_modules/dateparser/date.html
            # This is the case where I could not find a way to retrieve the date string.
                date_log_path = 3
                split_date = date.replace("(", "").replace(")", "").replace("[", "").split(" ")

                parsed_date = dateparser.date.DateDataParser().get_date_data(u'%s' % date)
                # if it doesn't work, we select the YYYY string.
                if parsed_date["date_obj"] is None: 
                    date_log_path = 4
                    date = re.search("(1[0-9][0-9][0-9])", date).group(0)
                else:
                    date_range = re.search("(1[0-9][0-9][0-9])", date).span()
                    date_log_path = 5
                    # We get the precision of the date: dateparser will autocomplete
                    # the date using the current date if it has only the month. That is not what we want.
                    if parsed_date["period"] == "month":
                        date = parsed_date["date_obj"].strftime('%Y-%m')
                    # This statement should never be true.
                    elif parsed_date["period"] == "year":
                        date = parsed_date["date_obj"].strftime('%Y')
                    else:
                        date = parsed_date["date_obj"].strftime('%Y-%m-%d')

                # Then we inject the normalised date in the @when attribute.
                desc_xml = desc.replace(unprocessed_date_string, f'<date xmlns=\u0022http://www.tei-c.org/ns/1.0\u0022 '
                                                             f'when=\u0022{date}\u0022>{unprocessed_date_string}</date>')

            # We update the dictionary.
            dict_values["date"] = date

        # If we do not match a gregorian year string (YYYY), but a republican year string ('an V', for instance),
        # we convert the republican date.
        elif republican_calendar_pattern.match(desc):
            date_log_path = 6
            date, date_string = tables.rep_greg_conversion.main(desc)
            if date_string is not None:
                desc_xml = desc.replace(date_string, f'<date xmlns=\u0022http://www.tei-c.org/ns/1.0\u0022 '
                                                     f'when=\u0022{date}\u0022>{date_string}</date>')
            else:
                desc_xml = desc
            dict_values["date"] = date
            dict_values["desc_xml"] = desc_xml
        else:
            dict_values["date"] = None
            no_date_trigger()
            desc_xml = desc
        # dict_values["date_range"] = date_range
        input_dict[id] = dict_values
        item[0] = desc_xml
    return output_dict


def isInt(string):
    try:
        int(string)
        result = isinstance(int(string), int)
    except:
        result = False
    return result


def is_float(string):
    try:
        float(string)
        result = isinstance(float(string), float)
    except:
        result = False
    return result


def is_roman(value):
    try:
        value in tables.conversion_tables.roman_to_arabic.keys()
        value = tables.conversion_tables.roman_to_arabic[value]
        return value
    except:
        return value


def length_extractor(descList, input_dict):
    """
    Extracts the lenghts from the list containing all of the tei:desc, and update the main dict.
    :param descList: the list containing all of the tei:desc
    :param input_dict: the dictionnary containing the data previously extracted (prices and dates)
    :return: a dict which keys are the ids, and which values are another dict with prices, dates and lenghts
    """
    print("Extracting length information")
    # This pattern works with the most frequent cases.
    length_pattern = re.compile(
        "([IVXivx0-9\/]{1,6})\.?\s(pages|page|pag.|p.)\s([0-5\/]{0,3})")
    pattern_fraction = re.compile("([0-9\/]{1,6})\s?de\s?p[ages]{0,3}\.?")
    for item in descList:
        desc, id = item[0], item[1]
        desc = clean_text(desc)
        desc = re.sub(r"\s+", " ", desc)
        desc = desc.replace("p/", "p")
        dict_values = input_dict[id]
        log_path = None
        length = None
        if re.search(length_pattern, desc):
            position_chaîne = re.search(length_pattern, desc).span()
            pn_search = re.search(length_pattern, desc)
            first_group = pn_search.group(1)
            second_group = pn_search.group(3)
            # If the second group is empty, there is no fraction.
            if second_group == "": 
                if first_group != "":
                    if isInt(is_roman(first_group.upper())):
                        length = int(is_roman(first_group.upper()))
                        log_path = 1
                    else:
                        try:
                            length = tables.conversion_tables.fractions_to_float[first_group]
                            log_path = 2
                        except:
                            length = f'key error, please check the transcription: {first_group}'
                            log_path = 3
            elif first_group != "" and second_group != "":
                if isInt(first_group):
                    value_1 = int(first_group)
                    log_path = 4
                else:
                    # The lenght can be in roman numbers.
                    value_1 = is_roman(first_group.upper())  
                    log_path = 5
                    if isInt(value_1):
                        log_path = 6
                        pass
                    else:
                        try:
                            value_1 = tables.conversion_tables.fractions_to_float[value_1]
                            log_path = 7
                        except:
                            value_1 = 501
                            log_path = 8
                if isInt(second_group):
                    value_2 = int(second_group)
                    log_path = 9
                else:
                    try:
                        value_2 = tables.conversion_tables.fractions_to_float[second_group]
                        log_path = 10
                    except:
                        value_2 = 404
                        log_path = 11
                length = float(value_1) + float(value_2)
            else:
                length = None
                log_path = 12
        elif re.search(pattern_fraction, desc):
            log_path = 13
            search = re.search("([0-9\/]{1,6})\s?de\s?p[age]{0,3}\.?", desc)
            position_chaîne = search.span()
            try:  # test to be removed after.
                length = tables.conversion_tables.fractions_to_float[search.group(1)]
            except:
                length = 0

        if length != None:
            starting_position = position_chaîne[0]
            ending_position = position_chaîne[1]
            # if a space is the last character of the identified range of page ("1 p. "), we can remove it.
            if desc[ending_position - 1] == " ": 
                ending_position = ending_position - 1
            desc_xml = f'{desc[:starting_position]}<measure xmlns=\u0022http://www.tei-c.org/ns/1.0\u0022' \
                       f' type=\u0022length\u0022 unit=\u0022p\u0022 n=\u0022{length}\u0022>' \
                       f'{desc[starting_position:ending_position]}</measure>{desc[ending_position:]}' \
            # desc_xml = desc
        else:
            desc_xml = desc
        # dict_values["groups"] = groups # for debugging purposes only
        # dict_values["path"] = path  # idem
        # dict_values["desc_xml"] = desc_xml
        dict_values["number_of_pages"] = length
        input_dict[id] = dict_values
        item[0] = desc_xml
    return input_dict


def format_extractor(descList, input_dict):
    """
    Extracts the format from the list containing all of the tei:desc, and update the main dict.
    :param descList: the list containing all of the tei:desc
    :param input_dict: the dictionnary containing the data previously extracted
    :return: a dict which keys are the ids, and which values are another dict 
    """
    print("Extracting format information")
    for item in descList:
        desc, id = item[0], item[1]
        desc_xml = desc
        ms_format = None
        dict_values = input_dict[id]
        format_simple_pattern = re.compile("(in-[0-9]{1,2}°?\.?\s?[obl]{0,3}\.?)")
        format_simple_pattern2 = re.compile("(in-folio\.?\s?[obl]{0,3}\.?)")
        format_simple_pattern3 = re.compile("(in-f[ol]{0,2}\.?\s?[obl]{0,3}\.?)")

        if re.search(format_simple_pattern, desc):
            format_search = re.search(format_simple_pattern, desc)
            ms_format = re.sub(r"\s$", "", format_search.group(1))
            position = format_search.span()
            start_position = position[0]
            end_position = position[1]

        elif re.search(format_simple_pattern2, desc):
            format_search = re.search(format_simple_pattern2, desc)
            ms_format = re.sub(r"\s$", "", format_search.group(1))
            position = format_search.span()
            start_position = position[0]
            end_position = position[1]

        elif re.search(format_simple_pattern3, desc):
            format_search = re.search(format_simple_pattern3, desc)
            ms_format = re.sub(r"\s$", "", format_search.group(1))
            position = format_search.span()
            start_position = position[0]
            end_position = position[1]
        else:
            desc_xml = desc
            start_position = None
            end_position = None


        # dict_values["desc_xml"] = desc_xml
        # let's improve the format identification: the "oblong" cases
        obl_pattern = re.compile(".*ob[l]{0,1}.*")
        format_pattern = re.compile("(in-[0-9]{1,2})")
        fol_pattern = re.compile(".*in\-f[olio]?.*")
        if ms_format is not None:
            if re.search(fol_pattern, ms_format):
                xml_encoded_format = '#document_format_1'
            elif re.search(format_pattern, ms_format):
                xml_encoded_format = re.search(format_pattern, ms_format).group(1)
                try:
                    xml_encoded_format = f'#document_format_{tables.conversion_tables.format_types[xml_encoded_format]}'
                except:
                    xml_encoded_format = None
            else:
                xml_encoded_format = None

            if xml_encoded_format is not None:
                if re.search(obl_pattern, ms_format):
                    xml_encoded_format = f'#document_format_{str(int(xml_encoded_format.split("_")[-1]) + 100)}'

        # Let's create the xml element
        if start_position and end_position:
            # if the last character of the identified format is a space, we remove it.
            if desc[end_position - 1] == " ":
                end_position = end_position - 1
            desc_xml = f"{desc[:start_position]}<measure xmlns=\u0022http://www.tei-c.org/ns/1.0\u0022 " \
                       f" type=\u0022format\u0022 unit=\u0022f\u0022 ana=\u0022{xml_encoded_format}\u0022>" \
                       f"{desc[start_position:end_position]}</measure>{desc[end_position:]}"
            # desc_xml = desc

        dict_values["desc_xml"] = desc_xml
        # xml_encoded_format is meant for the json output, while encoded_ms_format will
        # be the value of the @ana attribute, pointing to a taxonomy
        if xml_encoded_format is not None:
            encoded_ms_format = xml_encoded_format.split('_')[-1]
        else:
            xml_encoded_format = None
        dict_values["format"] = encoded_ms_format
        input_dict[id] = dict_values
        item[0] = desc_xml # we update the list
    return input_dict


def term_extractor(descList, input_dict):
    """
    Extracts the term from the list containing all of the tei:desc, and update the main dict.
    :param descList: the list containing all of the tei:desc
    :param input_dict: the dictionnary containing the data previously extracted
    :return: a dict which keys are the ids, and which values are another dict 
    """
    print("Extracting term information")
    for item in descList:
        desc, id, author, sell_date = item[0], item[1], item[2], item[3]
        desc_xml = desc
        term = None
        dict_values = input_dict[id]

        apas_pattern = re.compile("((Apostille)\s?a[utographe]{0,9}\.?\s?[signée]{0,6}\.?)")  # > Apas
        pas_pattern = re.compile("(([Pp]ièce|[Pp]\.)\s[^<]*?au[tographe]{1,8}\.?\s?si[gnée]{0,4}\.?)")  # > Pas
        pa_pattern = re.compile("(([Pp]ièce|[Pp]\.)(?!<)\s?[^<]*aut[ographe]{0,7}\.?)")  # > Pa
        ps_pattern = re.compile("(([Pp]ièce|[Pp]\.)\s?(signée|sig|sig\.|s\.))")  # > Ps
        bias_pattern = re.compile("((Billet|B\.)\s?a[utographe]{0,9}\.?\s?s[igné]{0,4}\.?)")  # > bias
        bis_pattern = re.compile("((Billet|B\.)\s?s[igné]{0,4}\.?)")  # > bis
        las_pattern = re.compile("((Lettre|Let\.|L\.)\s?a[utographe]{0,9}\.?\s?s[ignée]{0,5}\.?)")  # > Las
        la_pattern = re.compile("((Lettre|Let\.|L\.) a[utographe]{0,9}\.?)")  # > La
        ls_pattern = re.compile("((Lettre|Let\.|L\.) (signée|sig\.|s\.))")  # > Ls
        brs_pattern = re.compile("(Brevet\.?\s?[signé]{0,5}\.?)")  # > Brs
        qas_pattern = re.compile("(Quitt[ance]{0,4}?\.?\s?[autographe]{0,10}\.?\s?[signée]{0,6}\.?)")  # > Qas
        qs_pattern = re.compile("(Quitt[ance]{0,4}?\.?\s?[signée]{0,6}\.?)")  # > Qs
        ma_pattern = re.compile("([Mm]anuscrit aut[ographe]{0,7}\.?)")  # > Ma
        ca_pattern = re.compile("([Cc]hanson\saut[ographe]{0,7}\.?)")  # > Ca
        as_pattern = re.compile(
            "((Autographe|autographe|[Aa]ut\.|[Aa]\.)\s?s[ignée]{0,5}\.?)")  # > as # this one must be the last pattern tested.

        if re.search(pas_pattern, desc):
            term_search = re.search(pas_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["P.a.s."]}'

            correct_pattern = pas_pattern

        elif re.search(apas_pattern, desc):
            term_search = re.search(apas_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["Ap.a.s."]}'

            correct_pattern = apas_pattern


        elif re.search(ps_pattern, desc):
            term_search = re.search(ps_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["P.s."]}'

            correct_pattern = ps_pattern

        elif re.search(pa_pattern, desc):
            term_search = re.search(pa_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["P.a."]}'

            correct_pattern = pa_pattern


        elif re.search(bias_pattern, desc):
            term_search = re.search(bias_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["Bi.a.s."]}'

            correct_pattern = bias_pattern

        elif re.search(bis_pattern, desc):
            term_search = re.search(bis_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["Bi.s."]}'

            correct_pattern = bis_pattern


        elif re.search(las_pattern, desc):
            term_search = re.search(las_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["L.a.s."]}'

            correct_pattern = las_pattern

        elif re.search(la_pattern, desc):
            term_search = re.search(la_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["L.a."]}'

            correct_pattern = la_pattern

        elif re.search(brs_pattern, desc):
            term_search = re.search(brs_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["Br.s."]}'

            correct_pattern = brs_pattern

        elif re.search(qs_pattern, desc):
            term_search = re.search(qs_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["Q.s."]}'

            correct_pattern = qs_pattern

        elif re.search(ma_pattern, desc):
            term_search = re.search(ma_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["M.a."]}'

            correct_pattern = ma_pattern

        elif re.search(ca_pattern, desc):
            term_search = re.search(ca_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["C.a."]}'

            correct_pattern = ca_pattern

        elif re.search(qas_pattern, desc):
            term_search = re.search(qas_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["Q.a.s."]}'

            correct_pattern = qas_pattern

        elif re.search(ls_pattern, desc):
            term_search = re.search(ls_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["L.s."]}'

            correct_pattern = ls_pattern

        elif re.search(as_pattern, desc):  # keep this search the last one
            term_search = re.search(as_pattern, desc)
            term = re.sub(r"\s$", "", term_search.group(1))
            xml_norm_term = f'#document_type_{tables.conversion_tables.term_types["A.s."]}'

            correct_pattern = as_pattern

            # Check this problem (not matched by as_pattern):
            # "CAT_000096_e249": {
            #     "desc": "Rome, 20 juillet 1691; aut. sig. – 7 pag. – A M. de Lamoignon, avocat-général. (Très-curieuse.)",
            #     "price": null,
            #     "desc_xml": "Rome, 20 juillet 1691; aut. sig. – <measure xmlns=\"http://www.tei-c.org/ns/1.0\" quantity=\"7\" type=\"length\">7 pag.</measure> – A M. de <term xmlns=\"http://www.tei-c.org/ns/1.0\" type=\"format\">La</term>moignon, avocat-général. (Très-curieuse.)",
            #     "date": "1691-07-20",
            #     "number_of_pages": 7,
            #     "format": null,
            #     "term": "La"
            # },

        else:
            desc_xml = desc
            xml_norm_term = None
            correct_pattern = None

        # Let's create the xml element
        if correct_pattern:
            desc_xml = desc.replace(term, f'<term xmlns=\u0022http://www.tei-c.org/ns/1.0\u0022 '
                                                         f'ana=\"{xml_norm_term}\">{term}</term>')
        dict_values["desc_xml"] = desc_xml
        if xml_norm_term is not None:
            # norm_term is meant for the json output, while xml_norm_term is
            # the value of the @ana attribute, pointing to a taxonomy
            norm_term = xml_norm_term.split("_")[-1]
        else:
            norm_term = None
        dict_values["term"] = norm_term
        dict_values["author"] = author
        dict_values["sell_date"] = sell_date
        input_dict[id] = dict_values
    return input_dict


def no_price_trigger():
    """
    :return: Increases the counter when called
    """
    global no_price
    no_price += 1


def no_date_trigger():
    """
    :return: Increases the counter when called
    """
    global no_date
    no_date += 1


def desc_extractor(input):
    """
    This function extracts from an xml file all of the tei:desc elements
    :return: a list of lists that contains the tei:desc value, the date of the sale,
    """
    with open(input, 'r+') as fichier:
        f = etree.parse(fichier)
        root = f.getroot()
        desc = root.xpath("//tei:desc", namespaces=tei)
        list_desc = []
        sell_date = root.xpath("//tei:sourceDesc//tei:date", namespaces=tei)[0].text
        for i in desc:
            author = i.xpath("parent::tei:item/tei:name", namespaces=tei)
            try:
                price = i.xpath("parent::tei:item//tei:measure[@commodity='currency']/@quantity", namespaces=tei)[0]
            except:
                price = None
            # Only items with an @xml:id attribute are kept.
            id = i.xpath("@xml:id", namespaces=tei)
            if len(id) > 0: 
                id = id[0]
                if len(author) > 0:
                    author = author[0].text
                    try:
                        # We keep only the surname of the author.
                        author = author.split(" ")[0]
                        list_desc.append([i.text, id, author,  sell_date, price])
                    except:
                        author = None
                        list_desc.append([i.text, id, author,  sell_date, price])
                else:
                    author = None
                    list_desc.append([i.text, id, author, sell_date, price])
        return list_desc


def clean_text(input_text):
    """
    A function that cleans the text
    :param text: any string
    :return: the cleaned string
    """
    input_text = re.sub('\n', ' ', input_text)
    input_text = re.sub('\s+', ' ', input_text)
    output_text = re.sub('\s+$', '', input_text)
    return output_text


def conversion_to_list(path):
    """
    This function creates a global list gathering all tei:desc from the xml files.
    :param path:date
    :return: a list
    """
    final_list = []
    for xml_file in glob.iglob(path):
        for desc_element in desc_extractor(xml_file):
            final_list.append(desc_element)
    return final_list

# This is the taxonomy informations to add to the teiHeader of each output file.
xml_taxonomy = """
    <classDecl>
        <taxonomy xml:id="format">
           <desc>Document format</desc>
           <category xml:id="document_format_1">
              <catDesc>In-folio</catDesc>
           </category>
           <category xml:id="document_format_2">
              <catDesc>In-2°</catDesc>
           </category>
           <category xml:id="document_format_3">
              <catDesc>In-3°</catDesc>
           </category>
           <category xml:id="document_format_4">
              <catDesc>In-quarto</catDesc>
           </category>
           <category xml:id="document_format_8">
              <catDesc>In-octavo</catDesc>
           </category>
           <category xml:id="document_format_12">
              <catDesc>In-12</catDesc>
           </category>
           <category xml:id="document_format_16">
              <catDesc>In-16</catDesc>
           </category>
           <category xml:id="document_format_18">
              <catDesc>In-18</catDesc>
           </category>
           <category xml:id="document_format_32">
              <catDesc>In-32</catDesc>
           </category>
           <category xml:id="document_format_40">
              <catDesc>In-40</catDesc>
           </category>
           <category xml:id="document_format_48">
              <catDesc>In-48</catDesc>
           </category>
           <category xml:id="document_format_64">
              <catDesc>In-64</catDesc>
           </category>
           <category xml:id="document_format_101">
              <catDesc>In-folio oblong</catDesc>
           </category>
           <category xml:id="document_format_102">
              <catDesc>In-2° oblong</catDesc>
           </category>
           <category xml:id="document_format_103">
              <catDesc>In-3° oblong</catDesc>
           </category>
           <category xml:id="document_format_104">
              <catDesc>In-quarto oblong</catDesc>
           </category>
           <category xml:id="document_format_108">
              <catDesc>In-octavo oblong</catDesc>
           </category>
           <category xml:id="document_format_112">
              <catDesc>In-12 oblong</catDesc>
           </category>
           <category xml:id="document_format_116">
              <catDesc>In-16 oblong</catDesc>
           </category>
           <category xml:id="document_format_118">
              <catDesc>In-18 oblong</catDesc>
           </category>
           <category xml:id="document_format_132">
              <catDesc>In-32 oblong</catDesc>
           </category>
           <category xml:id="document_format_140">
              <catDesc>In-40 oblong</catDesc>
           </category>
           <category xml:id="document_format_148">
              <catDesc>In-48 oblong</catDesc>
           </category>
           <category xml:id="document_format_164">
              <catDesc>In-64 oblong</catDesc>
           </category>
        </taxonomy>
        <taxonomy xml:id="document_type">
           <desc>Document type</desc>
           <category xml:id="document_type_1">
              <catDesc>Apostille autographe signée</catDesc>
           </category>
           <category xml:id="document_type_2">
              <catDesc>Apostille autographe</catDesc>
           </category>
           <category xml:id="document_type_3">
              <catDesc>Pièce autographe</catDesc>
           </category>
           <category xml:id="document_type_4">
              <catDesc>Pièce signée</catDesc>
           </category>
           <category xml:id="document_type_5">
              <catDesc>Billet autographe signé</catDesc>
           </category>
           <category xml:id="document_type_6">
              <catDesc>Billet signé</catDesc>
           </category>
           <category xml:id="document_type_7">
              <catDesc>Lettre autographe signée</catDesc>
           </category>
           <category xml:id="document_type_8">
              <catDesc>Lettre autographe</catDesc>
           </category>
           <category xml:id="document_type_9">
              <catDesc>Lettre signée</catDesc>
           </category>
           <category xml:id="document_type_10">
              <catDesc>Brevet signé</catDesc>
           </category>
           <category xml:id="document_type_11">
              <catDesc>Quittance autographe signée</catDesc>
           </category>
           <category xml:id="document_type_12">
              <catDesc>Quittance signée</catDesc>
           </category>
           <category xml:id="document_type_13">
              <catDesc>Manuscrit autographe</catDesc>
           </category>
           <category xml:id="document_type_14">
              <catDesc>Chanson autographe</catDesc>
           </category>
           <category xml:id="document_type_15">
              <catDesc>Document (?) Autographe signé</catDesc>
           </category>
        </taxonomy>
    </classDecl>"""


def xml_output_production(dictionary, path):
    """
    This function is used to rewrite all the tei:desc of the output files with the new informations contained in the dictionary.
    param dictionary: the dictionary that contains all the informations produced.
    param path: a path to the output files to rewrite.
    """
    print("Updating the xml files")
    # For XPath search
    tei_namespace = "http://www.tei-c.org/ns/1.0"
    NSMAP1 = {'tei': tei_namespace}
    # http://effbot.org/zone/element-namespaces.htm#preserving-existing-namespace-attributes
    ElementTree.register_namespace("", tei_namespace)
 
    for xml_file in glob.iglob(path):
        with open(xml_file, 'r+') as fichier:
            tree = etree.parse(fichier)

            # Add taxonomy to the teiHeader.
            taxonomy = etree.fromstring(xml_taxonomy)
            tei_encodingDesc = tree.xpath('//tei:encodingDesc', namespaces=tei)[0]
            tei_encodingDesc.insert(1, taxonomy)

            # For each desc, with an @xml:id attribute, replace them with their enhanced desc retrieved from the dictionary.
            for desc in tree.xpath("//tei:desc[@xml:id]", namespaces=NSMAP1):
            	# For now, all desc don't have an @xml:id
                id = desc.xpath('./@xml:id')[0]
                desc_string = dictionary[id]["desc_xml"].replace("&", "&amp;")
                new_desc = etree.fromstring("<desc xmlns=\"http://www.tei-c.org/ns/1.0\" xml:id='%s'>%s</desc>" % (id, desc_string))
                desc.getparent().replace(desc, new_desc)

        # Rewrite the file with updated descs. 
        with open(xml_file.replace("clean", "tagged"), "w+") as sortie_xml:
            output = etree.tostring(tree, pretty_print=True, encoding='utf-8', xml_declaration=True).decode(
                        'utf8')
            sortie_xml.write(str(output))
            os.remove(xml_file)




if __name__ == "__main__":
    no_price = 0
    no_date = 0
    input_dir = args.input
    output_dir = '../output'
    files = '*_clean.xml'
    input_files = f'{input_dir}/{files}'
    output_files = f'{output_dir}/{files}'
    input_dir = os.path.dirname(input_files)

    try:
        # shutil.copytree contains a mkdir command, we have to delete the directory if it exists
        shutil.copytree(input_dir, output_dir)

    except:
        shutil.rmtree(output_dir)
        shutil.copytree(input_dir, output_dir)
    list_desc = conversion_to_list(input_files)
    output_dict = price_extractor(list_desc)
    output_dict = date_extractor(list_desc, output_dict)
    output_dict = length_extractor(list_desc, output_dict)
    output_dict = format_extractor(list_desc, output_dict)
    output_dict = term_extractor(list_desc, output_dict)

    # We write the xml output files.
    xml_output_production(output_dict, output_files)


    for key in output_dict:
        del output_dict[key]["desc_xml"]


    print("Done !")
    # print(f'Number of entries without price: {str(no_price)}')
    # print(f'Number of entries without date: {str(no_date)}')
