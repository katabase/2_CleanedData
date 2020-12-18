# Cleaned Data - level 2

This repository contains digitised manuscripts sale catalogs encoded in XML-TEI at level 2.

The data have been cleaned (level 2) but not post-processed ([level 3](https://github.com/katabase/3_TaggedData)) yet.

## Schema

You can find the ODD that validates the encoding in the repository `schema`.

## Workflow

Once the data have been cleaned, we can start to extract information from the `desc`.

`extractor-xml.py` extracts informations and then retrieves them in the same XML file (level 3). 

The script transforms this


```xml
<item n="80" xml:id="CAT_000146_e80">
   <num>80</num>
   <name type="author">Cherubini (L.),</name>
   <trait>
      <p>l'illustre compositeur</p>
   </trait>
   <desc>L. a. s.; 1836, 1 p. in-8.</desc>
    <measure commodity="currency" unit="FRF" quantity="12">12</measure>
</item>
```

into


```xml
<item n="80" xml:id="CAT_000146_e80">
   <num>80</num>
   <name type="author">Cherubini (L.),</name>
   <trait>
      <p>l'illustre compositeur</p>
   </trait>
   <desc>
      <term>L. a. s.</term>;<date>1836</date>,
   	<measure type="length" unit="p" n="1">1 p.</measure> 
   	<measure unit="f" type="format" n="8">in-8</measure>.
   	<measure commodity="currency" unit="FRF" quantity="12">12</measure>
   </desc>
</item>
```

To carry this task we use `extractor_xml.py` [[available here](https://github.com/katabase/2_CleanedData/tree/master/script/extractor-xml.py)].

## Installation and use

```bash
* git clone https://github.com/katabase/2_CleanedData.git
* cd 2_CleanedData
* python3 -m venv my_env
* source my_env/bin/activate
* pip install -r requirements.txt
* cd script 
* python3 extractor_xml.py directory_to_process
```

**Note that you have to be in the folder `script`to execute `extractor_xml.py`.**

The output files will be in the folder `output`.

## Credits

* Scripts were created by Matthias Gille Levenson and improved by Alexandre Bartz with the help of Simon Gabay.
* The catalogs were encoded by Lucie Rondeau du Noyer, Simon Gabay, Matthias Gille Levenson, Ljudmila Petkovic and Alexandre Bartz.


## Cite this repository
Alexandre Bartz, Simon Gabay, Matthias Gille Levenson, Ljudmila Petkovic and Lucie Rondeau du Noyer, _Manuscript sale catalogues_, Neuchâtel: Université de Neuchâtel, 2020, [https://github.com/katabase/2_CleanedData](https://github.com/katabase/2_CleanedData).

## Licence
<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Licence Creative Commons" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International Licence</a>.
