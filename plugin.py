#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import tempfile, shutil
import re
import inspect
import xml.etree.ElementTree as ET
PY2 = sys.version_info[0] == 2
if PY2:
    import ConfigParser as configparser
else:
    import configparser

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from random import randint
from html_namedentities import named_entities
from epub_utils import epub_zip_up_book_contents

if PY2:
    import Tkinter as tkinter
    import ttk as tkinter_ttk
    import Tkconstants as tkinter_constants
    import tkFileDialog as tkinter_filedialog
else:
    import tkinter
    import tkinter.ttk as tkinter_ttk
    import tkinter.constants as tkinter_constants
    import tkinter.filedialog as tkinter_filedialog

_USER_HOME = os.path.expanduser("~")
SCRIPT_DIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
IS_NAMED_ENTITY = re.compile("(&\w+;)")
BORKIFY_METHOD = 1

ini_path = os.path.join(SCRIPT_DIR, 'Borkify.ini')

def write_ini(ini_path):
    config = configparser.ConfigParser(allow_no_value = True)
    config.optionxform = str
    config.add_section('Borkifier')
    config.set('Borkifier', '; Language can have four values:')
    config.set('Borkifier', '; 0: random for each text element (e.g. a span inside a paragraph can have different settings)')
    config.set('Borkifier', '; 1: text will resemble speech from the Swedish Chef')
    config.set('Borkifier', '; 2: text will resemble speech from Elmer Fudd')
    config.set('Borkifier', '; 3: text will resemble the "Olde English" speech')
    config.set('Borkifier', 'Language', str(BORKIFY_METHOD))
    with open(ini_path, 'w') as fp:
        config.write(fp)

def read_ini(ini_path):
    config = configparser.ConfigParser(allow_no_value = True)
    config.read(ini_path)
    os.path.isfile(ini_path)
    BORKIFY_METHOD = config.getint('Borkifier', 'Language')

def run(bk):
    # check if inifile exists
    if not os.path.isfile(ini_path):
            print ("Borkify.ini not found. Using default settings.")
            write_ini(ini_path)
    
	# run plugin version check
    href = 'http://www.mobileread.com/forums/showpost.php?p=3138237&postcount=1'
    _latest_pattern = re.compile(r'Current Version:\s*&quot;([^&]*)&')
    plugin_xml_path = os.path.abspath(os.path.join(bk._w.plugin_dir, 'Borkify', 'plugin.xml'))
    plugin_version = ET.parse(plugin_xml_path).find('.//version').text
    try:
        latest_version = None
        if PY2:
            response = urllib.urlopen(href)
        else:
            response = urllib.request.urlopen(href)
        m = _latest_pattern.search(response.read().decode('utf-8', 'ignore'))
        if m:
            latest_version = (m.group(1).strip())
            if latest_version and latest_version != plugin_version:
                restype = 'info'
                filename = linenumber = None
                message = '*** An updated plugin version is available: v' + latest_version + ' ***'
                bk.add_result(restype, filename, linenumber, message)
    except:
        pass
	
    # read inifile
    read_ini(ini_path)
    
    # Extract book
    temp_dir = tempfile.mkdtemp()
    bk.copy_book_contents_to(temp_dir)

    # create mimetype file
    os.chdir(temp_dir)
    mimetype = open("mimetype", "w")
    mimetype.write("application/epub+zip")
    mimetype.close()
    
    # parse all xhtml/html files
    for mid, href in bk.text_iter():
        print("..converting: ", href, " with manifest id: ", mid)
        data = borkify_xhtml(bk, mid, href)

        # write out modified file
        destdir = ""
        filename = unquote(href)
        if "/" in href:
            destdir, filename = unquote(filename).split("/")
        fpath = os.path.join(temp_dir, "OEBPS", destdir, filename)
        with open(fpath, "wb") as f:
            f.write(data.encode('utf-8'))
   
     # finally ready to build epub
    print("..creating 'borkified' ePUB")
    data = "application/epub+zip"
    fpath = os.path.join(temp_dir,"mimetype")
    with open(fpath, "wb") as f:
        f.write(data.encode('utf-8'))

    # ask the user where he/she wants to store the new epub
    doctitle = "dummy"
    fname = cleanup_file_name(doctitle) + "_borkified.epub"
    localRoot = tkinter.Tk()
    localRoot.withdraw()
    fpath = tkinter_filedialog.asksaveasfilename(
        parent=localRoot,
        title="Save ePUB as ...",
        initialfile=fname,
        initialdir=_USER_HOME,
        defaultextension=".epub"
        )

    # localRoot.destroy()
    localRoot.quit()
    if not fpath:
        ignore_errors = sys.platform == 'win32'
        shutil.rmtree(temp_dir, ignore_errors)
        print("Borkify plugin cancelled by user")
        return 0

    epub_zip_up_book_contents(temp_dir, fpath)
    ignore_errors = sys.platform == 'win32'
    shutil.rmtree(temp_dir, ignore_errors)

    print("Output Conversion Complete")

 	# Setting the proper Return value is important.
 	# 0 - means success
 	# anything else means failure

    return 0

def borkify_xhtml(bk, mid, href):
    res = []
 
    #parse the xhtml, converting on the fly to update it
    qp = bk.qp
    qp.setContent(bk.readfile(mid))
    basetags_end=('.p', '.div','.li','.td')
    basetags_middle=('.p.', '.div.','.li.','.td.')
    for text, tprefix, tname, ttype, tattr in qp.parse_iter():
        if text is not None:
            if "pre" not in tprefix:
                text = convert_named_entities(text)
            if filter(tprefix.endswith,basetags_end) or (any(substring in tprefix for substring in basetags_middle)):
                text = borkify(text)
            res.append(text)
        
        res.append(qp.tag_info_to_xml(tname, ttype, tattr))
   
    return "".join(res)

def borkify(text):
    if BORKIFY_METHOD == 0:
        method = randint(1,3)
    else:
        method = BORKIFY_METHOD
    
    if method == 1:
        text = chefalize(text)
    elif method == 2:
        text = fuddalize(text)
    else:
        text = oldalize(text)
        
    return text
 
def convert_named_entities(text): 
    pieces = IS_NAMED_ENTITY.split(text)
    for i in range(1, len(pieces),2):
        piece = pieces[i]
        sval = named_entities.get(piece[1:],"")
        if sval != "":
            val = ord(sval)
            piece = "&#%d;" % val
            pieces[i] =piece
    return "".join(pieces)

def cleanup_file_name(name):
    import string
    _filename_sanitize = re.compile(r'[\xae\0\\|\?\*<":>\+/]')
    substitute='_'
    one = ''.join(char for char in name if char in string.printable)
    one = _filename_sanitize.sub(substitute, one)
    one = re.sub(r'\s', '_', one).strip()
    one = re.sub(r'^\.+$', '_', one)
    one = one.replace('..', substitute)
    # Windows doesn't like path components that end with a period
    if one.endswith('.'):
        one = one[:-1]+substitute
    # Mac and Unix don't like file names that begin with a full stop
    if len(one) > 0 and one[0:1] == '.':
        one = substitute+one[1:]
    return one

def chefalize(phrase):
    #based on the classic chef.x, copyright (c) 1992, 1993 John Hagerman
    subs = ((r'a([nu])', r'u\1'),
            (r'A([nu])', r'U\1'),
            (r'a\B', r'e'),
            (r'A\B', r'E'),
            (r'en\b', r'ee'),
            (r'\Bew', r'oo'),
            (r'\Be\b', r'e-a'),
            (r'\be', r'i'),
            (r'\bE', r'I'),
            (r'\Bf', r'ff'),
            (r'\Bir', r'ur'),
            (r'(\w*?)i(\w*?)$', r'\1ee\2'),
            (r'\bow', r'oo'),
            (r'\bo', r'oo'),
            (r'\bO', r'Oo'),
            (r'the', r'zee'),
            (r'The', r'Zee'),
            (r'th\b', r't'),
            (r'\Btion', r'shun'),
            (r'\Bu', r'oo'),
            (r'\BU', r'Oo'),
            (r'v', r'f'),
            (r'V', r'F'),
            (r'w', r'w'),
            (r'W', r'W'),
            (r'([a-z])[.]', r'\1.  Bork Bork Bork!'))

    for fromPattern, toPattern in subs:
        phrase = re.sub(fromPattern, toPattern, phrase)
    return phrase

def fuddalize(phrase):
    subs = ((r'[rl]', r'w'),
            (r'qu', r'qw'),
            (r'th\b', r'f'),
            (r'th', r'd'),
            (r'n[.]', r'n, uh-hah-hah-hah.'))

    for fromPattern, toPattern in subs:
        phrase = re.sub(fromPattern, toPattern, phrase)
    return phrase
   
def oldalize(phrase):
    subs = ((r'i([bcdfghjklmnpqrstvwxyz])e\b', r'y\1'),
            (r'i([bcdfghjklmnpqrstvwxyz])e', r'y\1\1e'),
            (r'ick\b', r'yk'),
            (r'ia([bcdfghjklmnpqrstvwxyz])', r'e\1e'),
            (r'e[ea]([bcdfghjklmnpqrstvwxyz])', r'e\1e'),
            (r'([bcdfghjklmnpqrstvwxyz])y', r'\1ee'),
            (r'([bcdfghjklmnpqrstvwxyz])er', r'\1re'),
            (r'([aeiou])re\b', r'\1r'),
            (r'ia([bcdfghjklmnpqrstvwxyz])', r'i\1e'),
            (r'tion\b', r'cioun'),
            (r'ion\b', r'ioun'),
            (r'aid', r'ayde'),
            (r'ai', r'ey'),
            (r'ay\b', r'y'),
            (r'ay', r'ey'),
            (r'ant', r'aunt'),
            (r'ea', r'ee'),
            (r'oa', r'oo'),
            (r'ue', r'e'),
            (r'oe', r'o'),
            (r'ou', r'ow'),
            (r'ow', r'ou'),
            (r'\bhe', r'hi'),
            (r've\b', r'veth'),
            (r'se\b', r'e'),
            (r"'s\b", r'es'),
            (r'ic\b', r'ick'),
            (r'ics\b', r'icc'),
            (r'ical\b', r'ick'),
            (r'tle\b', r'til'),
            (r'll\b', r'l'),
            (r'ould\b', r'olde'),
            (r'own\b', r'oune'),
            (r'un\b', r'onne'),
            (r'rry\b', r'rye'),
            (r'est\b', r'este'),
            (r'pt\b', r'pte'),
            (r'th\b', r'the'),
            (r'ch\b', r'che'),
            (r'ss\b', r'sse'),
            (r'([wybdp])\b', r'\1e'),
            (r'([rnt])\b', r'\1\1e'),
            (r'from', r'fro'),
            (r'when', r'whan'))
            
    for fromPattern, toPattern in subs:
        phrase = re.sub(fromPattern, toPattern, phrase)
    return phrase

def main():
    print ("I reached main when I should not have\n")
    return -1
    
if __name__ == "__main__":
    sys.exit(main())