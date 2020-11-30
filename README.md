# Cleaned Data - level 2

This repository contains digitised manuscripts sale catalogs encoded in XML-TEI at level 2.

The data have been cleaned (level 2) but not post-processed (level 3) yet.

## Workflow

Once the data have been cleaned, we can start to extract information from the `desc`.

EXTRACTOR-XML extracts informations and then retrieves them in an XML file (level 3). 

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
   <desc><term>L. a. s.</term>;<date>1836</date>,
   	<measure type="length" unit="p" n="1">1 p.</measure> 
   	<measure unit="f" type="format" n="8">in-8</measure>.
   	<measure commodity="currency" unit="FRF" quantity="12">12</measure></desc>
</item>
```

To carry this task we use the `???.py` [[available here](https://github.com/katabase/2_CleanedData/tree/master/script/???)].


## Cite this repository
Alexandre Bartz, Simon Gabay, Matthias Gille Levenson, Ljudmila Petkovic and Lucie Rondeau du Noyer, _Manuscript sale catalogues_, Neuchâtel: Université de Neuchâtel, 2019, [https://github.com/katabase/2_CleanedData](https://github.com/katabase/2_CleanedData).

## Licence
<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Licence Creative Commons" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International Licence</a>.