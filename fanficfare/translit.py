#-*-coding:utf-8-*-
# Code taken from http://python.su/forum/viewtopic.php?pid=66946
from __future__ import absolute_import

# py2 vs py3 transition
from .six import text_type as unicode
from .six import ensure_text

import unicodedata
def is_syllable(letter):
    syllables = ("A", "E", "I", "O", "U", "a", "e", "i", "o", "u")
    if letter in syllables:
        return True
    return False
def is_consonant(letter):
    return not is_syllable(letter)
def romanize(letter):
    try:
        unicode(letter)
    except UnicodeEncodeError:
        pass
    else:
        return unicode(letter)
    unid = unicodedata.name(letter)
    exceptions = {"NUMERO SIGN": "No", "LEFT-POINTING DOUBLE ANGLE QUOTATION MARK": "\"", "RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK": "\"", "DASH": "-"}
    for name_contains in exceptions:
        if unid.find(name_contains)!=-1:
            return exceptions[name_contains]
    assert(unid.startswith("CYRILLIC"))# Not ready to romanize anything but cyrillics
    transformation_pairs = {"CYRILLIC CAPITAL LETTER ": str.capitalize, "CYRILLIC SMALL LETTER ": str.lower}
    func = str.lower
    for name_contains in transformation_pairs:
        if unid.find(name_contains)!=-1:
            func = transformation_pairs[name_contains]
            unid = unid.replace(name_contains, "")
    cyrillic_exceptions = {"YERU": "y", "SHORT I": "y", "HARD SIGN": "\'", "SOFT SIGN": "\'", "BYELORUSSIAN-UKRAINIAN I": "i", "GHE WITH UPTURN": "g", "UKRAINIAN IE": "ie", "YU": "yu", "YA": "ya"}
    for name_contains in cyrillic_exceptions:
        if unid.find(name_contains)!=-1:
            return cyrillic_exceptions[name_contains]
    if all(map(is_syllable, unid)):
        return func(unid)
    else:
        return func(filter(is_consonant, unid))
def translit(text):
    output = ""
    for letter in ensure_text(text):
        output += romanize(letter)
    return output
#def main():
    #text = u"русск.: Любя, съешь щипцы, — вздохнёт мэр, — кайф жгуч."
    #print translit(text)
    #text = u"укр.: Гей, хлопці, не вспію - на ґанку ваша файна їжа знищується бурундучком."
    #print translit(text)
    #text = u"болг.: Ах, чудна българска земьо, полюшквай цъфтящи жита."
    #print translit(text)
    #text = u"серб.: Неуредне ноћне даме досађивале су Џеку К."
    #print translit(text)
    #russk.: Lyubya, s'iesh' shchiptsy, - vzdohniot mer, - kayf zhghuch.
    #ukr.: Ghiey, hloptsi, nie vspiyu - na ganku vasha fayna yzha znishchuiet'sya burunduchkom.
    #bolgh.: Ah, chudna b'lgharska ziem'o, polyushkvay ts'ftyashchi zhita.
    #sierb.: Nieuriednie notshnie damie dosadjivalie su Dzhieku K.
if __name__=="__main__":
    main()
